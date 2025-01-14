import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

#Initialising OpenTelemetry Tracing
trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "course-catalog-service"}))
)

# Jaeger Exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",  # Jaeger agent hostname
    agent_port=9411,             # New Jaeger agent port
)

# Span processor to the tracer provider
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(jaeger_exporter))

# Auto-instrument for the Flask application
FlaskInstrumentor().instrument_app(app)

# Getting tracer
tracer = trace.get_tracer(__name__)

# tracer.start_as_current_span: used to start a span and set it as the current span in the context.

# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    with tracer.start_as_current_span("load_courses"):
        if not os.path.exists(COURSE_FILE):
            return []  # Return an empty list if the file doesn't exist
        with open(COURSE_FILE, 'r') as file:
            return json.load(file)



def save_courses(data):
    """Save new course data to the JSON file."""
    with tracer.start_as_current_span("save_courses"):
        courses = load_courses()  # Load existing courses
        courses.append(data)  # Append the new course
        with open(COURSE_FILE, 'w') as file:
            json.dump(courses, file, indent=4)


# Routes
@app.route('/')
def index():
    with tracer.start_as_current_span("index_page"):
        return render_template('index.html')


@app.route('/catalog')
def course_catalog():
    with tracer.start_as_current_span("course_catalog"):
        courses = load_courses()
        return render_template('course_catalog.html', courses=courses)


@app.route('/course/<code>')
def course_details(code):
    with tracer.start_as_current_span("course_details") as span:
        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            span.set_attribute("error", True)
            flash(f"No course found with code '{code}'.", "error")
            return redirect(url_for('course_catalog'))
        span.set_attribute("course_code", code)
        return render_template('course_details.html', course=course)


@app.route('/save_course', methods=['POST'])
def save_course():
    with tracer.start_as_current_span("save_course") as span:
        try:
            name = request.form['name']
            code = request.form['code']
            description = request.form['description']
            instructor = request.form['instructor']
            new_course = {
                'name': name,
                'code': code,
                'description': description,
                'instructor': instructor
            }
            save_courses(new_course)
            # span.attribute: used to set attributes to the span.
            span.set_attribute("course_name", name)
            span.set_attribute("course_code", code)
            flash("Course added successfully!", "success")
        except Exception as e:
            span.set_attribute("error", True)
            flash("Failed to add course.", "error")
        return redirect(url_for('course_catalog'))


@app.route('/delete_course/<code>', methods=['POST'])
def delete_course(code):
    with tracer.start_as_current_span("delete_course") as span:
        courses = load_courses()
        updated_courses = [course for course in courses if course['code'] != code]
        with open(COURSE_FILE, 'w') as file:
            json.dump(updated_courses, file, indent=4)
        span.set_attribute("deleted_course_code", code)
        flash(f"Course with code '{code}' has been deleted.", "success")
        return redirect(url_for('course_catalog'))


@app.route('/add_course')
def add_course():
    with tracer.start_as_current_span("add_course_page"):
        return render_template('add_course.html')


if __name__ == '__main__':
    app.run(debug=True)

