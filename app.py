from datetime import date
from flask import Flask, abort, redirect, render_template_string, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vehicles.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

STATUSES = ["Active", "In Service", "Retired"]


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(30), unique=True, nullable=False)
    make = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    mileage = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="Active")
    last_service = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<Vehicle {self.vehicle_number}>"


BASE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} · Fleet Manager</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font: 15px/1.5 system-ui, sans-serif; color: #172033; background: #f4f6fa; }
    header { background: #172033; color: white; padding: 16px 5%; display: flex; justify-content: space-between; }
    header a { color: white; text-decoration: none; font-weight: 700; }
    main { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
    h1 { margin-bottom: 8px; }
    .muted { color: #64748b; }
    .cards { display: flex; gap: 14px; margin: 22px 0; flex-wrap: wrap; }
    .card, .panel { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; }
    .card { min-width: 160px; flex: 1; }
    .number { display: block; font-size: 27px; font-weight: 700; }
    .toolbar { display: flex; justify-content: space-between; gap: 12px; margin: 18px 0; flex-wrap: wrap; }
    form.inline { display: flex; gap: 8px; flex-wrap: wrap; }
    input, select { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; }
    .btn { display: inline-block; padding: 9px 13px; border: 0; border-radius: 6px; background: #2563eb; color: white; text-decoration: none; cursor: pointer; font: inherit; }
    .btn.secondary { background: #475569; }
    .btn.danger { background: #dc2626; }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { padding: 12px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }
    th { color: #475569; font-size: 13px; }
    .panel { overflow-x: auto; padding: 0; }
    .actions { display: flex; gap: 7px; align-items: center; }
    .actions form { margin: 0; }
    .badge { border-radius: 20px; background: #e2e8f0; padding: 4px 9px; font-size: 12px; }
    .badge.active { background: #dcfce7; color: #166534; }
    .badge.service { background: #fef3c7; color: #92400e; }
    .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .field { display: flex; flex-direction: column; gap: 5px; }
    .field input, .field select { width: 100%; }
    .full { grid-column: 1 / -1; }
    .flash { background: #dbeafe; padding: 10px 14px; border-radius: 6px; margin: 12px 0; }
    @media (max-width: 650px) { .form-grid { grid-template-columns: 1fr; } .full { grid-column: auto; } }
  </style>
</head>
<body>
<header>
  <a href="{{ url_for('index') }}">🚗 Fleet Manager</a>
  <span>Vehicle Management System</span>
</header>
<main>
  {% with messages = get_flashed_messages() %}
    {% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
  {% endwith %}
  {{ content|safe }}
</main>
</body>
</html>
"""

INDEX = """
<h1>Fleet dashboard</h1>
<p class="muted">Manage vehicles and monitor their status.</p>

<div class="cards">
  <div class="card"><span class="muted">Total vehicles</span><span class="number">{{ total }}</span></div>
  <div class="card"><span class="muted">Active</span><span class="number">{{ active }}</span></div>
  <div class="card"><span class="muted">In service</span><span class="number">{{ in_service }}</span></div>
  <div class="card"><span class="muted">Retired</span><span class="number">{{ retired }}</span></div>
</div>

<div class="toolbar">
  <form class="inline" method="get">
    <input name="q" value="{{ q }}" placeholder="Search registration, make, model">
    <select name="status">
      <option value="">All statuses</option>
      {% for item in statuses %}
        <option value="{{ item }}" {% if status == item %}selected{% endif %}>{{ item }}</option>
      {% endfor %}
    </select>
    <button class="btn secondary" type="submit">Search</button>
    <a class="btn secondary" href="{{ url_for('index') }}">Reset</a>
  </form>
  <a class="btn" href="{{ url_for('create_vehicle') }}">+ Add vehicle</a>
</div>

<div class="panel">
<table>
  <thead><tr>
    <th>Vehicle number</th><th>Vehicle</th><th>Year</th><th>Mileage</th>
    <th>Status</th><th>Last service</th><th>Actions</th>
  </tr></thead>
  <tbody>
  {% for vehicle in vehicles %}
    <tr>
      <td>{{ vehicle.vehicle_number }}</td>
      <td>{{ vehicle.make }} {{ vehicle.model }}</td>
      <td>{{ vehicle.year }}</td>
      <td>{{ "{:,}".format(vehicle.mileage) }} km</td>
      <td><span class="badge {{ vehicle.status|lower|replace(' ', '-') }}">{{ vehicle.status }}</span></td>
      <td>{{ vehicle.last_service.strftime("%Y-%m-%d") if vehicle.last_service else "—" }}</td>
      <td>
        <div class="actions">
          <a class="btn secondary" href="{{ url_for('edit_vehicle', vehicle_id=vehicle.id) }}">Edit</a>
          <form method="post" action="{{ url_for('delete_vehicle', vehicle_id=vehicle.id) }}"
                onsubmit="return confirm('Delete this vehicle?')">
            <button class="btn danger" type="submit">Delete</button>
          </form>
        </div>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="7" class="muted">No vehicles found. Add a vehicle to get started.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
"""

FORM = """
<h1>{{ heading }}</h1>
<p class="muted">Enter the vehicle details below.</p>
<div class="panel" style="padding: 20px">
<form method="post">
  <div class="form-grid">
    <label class="field">Vehicle number
      <input name="vehicle_number" required maxlength="30" value="{{ vehicle.vehicle_number if vehicle else '' }}">
    </label>
    <label class="field">Make
      <input name="make" required maxlength="60" value="{{ vehicle.make if vehicle else '' }}">
    </label>
    <label class="field">Model
      <input name="model" required maxlength="60" value="{{ vehicle.model if vehicle else '' }}">
    </label>
    <label class="field">Year
      <input name="year" type="number" min="1900" max="2100" required value="{{ vehicle.year if vehicle else '' }}">
    </label>
    <label class="field">Mileage (km)
      <input name="mileage" type="number" min="0" required value="{{ vehicle.mileage if vehicle else 0 }}">
    </label>
    <label class="field">Status
      <select name="status">
        {% for item in statuses %}
          <option value="{{ item }}" {% if vehicle and vehicle.status == item %}selected{% endif %}>{{ item }}</option>
        {% endfor %}
      </select>
    </label>
    <label class="field">Last service date
      <input name="last_service" type="date"
        value="{{ vehicle.last_service.isoformat() if vehicle and vehicle.last_service else '' }}">
    </label>
    <div class="full">
      <button class="btn" type="submit">Save vehicle</button>
      <a class="btn secondary" href="{{ url_for('index') }}">Cancel</a>
    </div>
  </div>
</form>
</div>
"""


def page(title, content, **context):
    return render_template_string(BASE, title=title,
                                  content=render_template_string(content, **context))


def get_vehicle_or_404(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if vehicle is None:
        abort(404)
    return vehicle


def read_form(vehicle=None):
    """Validate and save form fields. Returns an error message or None."""
    vehicle_number = request.form.get("vehicle_number", "").strip().upper()
    make = request.form.get("make", "").strip()
    model = request.form.get("model", "").strip()

    try:
        year = int(request.form.get("year", ""))
        mileage = int(request.form.get("mileage", ""))
    except ValueError:
        return "Year and mileage must be whole numbers."

    if not vehicle_number or not make or not model:
        return "Vehicle number, make, and model are required."
    if not 1900 <= year <= 2100 or mileage < 0:
        return "Enter a valid year and a non-negative mileage."

    duplicate = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()
    if duplicate and (vehicle is None or duplicate.id != vehicle.id):
        return "That vehicle number is already in use."

    status = request.form.get("status", "Active")
    if status not in STATUSES:
        return "Choose a valid vehicle status."

    service_text = request.form.get("last_service", "").strip()
    try:
        last_service = date.fromisoformat(service_text) if service_text else None
    except ValueError:
        return "Enter a valid service date."

    if vehicle is None:
        vehicle = Vehicle()
        db.session.add(vehicle)

    vehicle.vehicle_number = vehicle_number
    vehicle.make = make
    vehicle.model = model
    vehicle.year = year
    vehicle.mileage = mileage
    vehicle.status = status
    vehicle.last_service = last_service
    db.session.commit()
    return None


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")

    query = Vehicle.query
    if q:
        search = f"%{q}%"
        query = query.filter(or_(
            Vehicle.vehicle_number.ilike(search),
            Vehicle.make.ilike(search),
            Vehicle.model.ilike(search),
        ))
    if status in STATUSES:
        query = query.filter_by(status=status)

    vehicles = query.order_by(Vehicle.vehicle_number).all()
    return page(
        "Dashboard", INDEX, vehicles=vehicles, q=q, status=status,
        statuses=STATUSES, total=Vehicle.query.count(),
        active=Vehicle.query.filter_by(status="Active").count(),
        in_service=Vehicle.query.filter_by(status="In Service").count(),
        retired=Vehicle.query.filter_by(status="Retired").count(),
    )


@app.route("/vehicles/new", methods=["GET", "POST"])
def create_vehicle():
    if request.method == "POST":
        error = read_form()
        if error:
            return page("Add vehicle", FORM, heading="Add vehicle",
                        vehicle=None, statuses=STATUSES, error=error), 400
        return redirect(url_for("index"))

    return page("Add vehicle", FORM, heading="Add vehicle",
                vehicle=None, statuses=STATUSES)


@app.route("/vehicles/<int:vehicle_id>/edit", methods=["GET", "POST"])
def edit_vehicle(vehicle_id):
    vehicle = get_vehicle_or_404(vehicle_id)
    if request.method == "POST":
        error = read_form(vehicle)
        if error:
            return page("Edit vehicle", FORM, heading="Edit vehicle",
                        vehicle=vehicle, statuses=STATUSES, error=error), 400
        return redirect(url_for("index"))

    return page("Edit vehicle", FORM, heading="Edit vehicle",
                vehicle=vehicle, statuses=STATUSES)


@app.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
def delete_vehicle(vehicle_id):
    vehicle = get_vehicle_or_404(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    return redirect(url_for("index"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
