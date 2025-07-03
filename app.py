from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import io
import os
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "clave-super-secreta"


# Conexión a MongoDB local
client = MongoClient("mongodb://localhost:27017/")
db = client["GodsPlanDB"]
estudiantes = db["Estudiantes"]
catequistas = db["Catequistas"]
libros = db["Libros"]
nivelcatequesis = db["NivelCatequesis"]
parroquias = db["Parroquias"]
personas = db["Personas"]
sacramentos = db["Sacramentos"]


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        fecha_nacimiento = request.form["fecha_nacimiento"]
        direccion = request.form["direccion"]
        telefono = request.form["telefono"]
        parroquia = request.form["parroquia"]
        sacramento = request.form["sacramento"]

        nuevo_estudiante = {
            "nombre": nombre,
            "fecha_nacimiento": fecha_nacimiento,
            "direccion": direccion,
            "telefono": telefono,
            "parroquia": parroquia,
            "sacramento": sacramento
        }

        estudiantes.insert_one(nuevo_estudiante)
        flash("Estudiante registrado correctamente.", "success")
        return redirect("/consultas")


    return render_template("registro.html")

@app.route("/consultas")
def consultas():
    sacramento_filtro = request.args.get("sacramento")
    parroquia_filtro = request.args.get("parroquia")

    query = {}
    if sacramento_filtro:
        query["sacramento"] = sacramento_filtro
    if parroquia_filtro:
        query["parroquia"] = parroquia_filtro

    estudiantes_cursor = estudiantes.find(query)
    estudiantes_lista = []
    for est in estudiantes_cursor:
        est["_id"] = str(est["_id"])
        estudiantes_lista.append(est)

    total = estudiantes.count_documents({})
    parroquias = estudiantes.distinct("parroquia")

    # Conteo por sacramento
    sacramento_count = estudiantes.aggregate([
        {"$group": {"_id": "$sacramento", "cantidad": {"$sum": 1}}}
    ])
    sacramento_stats = {item["_id"]: item["cantidad"] for item in sacramento_count if item["_id"]}

    # Conteo por parroquia
    parroquia_count = estudiantes.aggregate([
        {"$group": {"_id": "$parroquia", "cantidad": {"$sum": 1}}}
    ])
    parroquia_stats = {item["_id"]: item["cantidad"] for item in parroquia_count if item["_id"]}

    return render_template("consultas.html",
                           estudiantes=estudiantes_lista,
                           total=total,
                           parroquias=parroquias,
                           sacramento_filtro=sacramento_filtro,
                           parroquia_filtro=parroquia_filtro,
                           sacramento_stats=sacramento_stats,
                           parroquia_stats=parroquia_stats)




@app.route("/eliminar/<id>")
def eliminar(id):
    try:
        estudiantes.delete_one({"_id": ObjectId(id)})
        flash("Estudiante eliminado correctamente.", "danger")

    except Exception as e:
        print(f"Error al eliminar: {e}")
    return redirect("/consultas")

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    est = estudiantes.find_one({"_id": ObjectId(id)})

    if request.method == "POST":
        nuevo_dato = {
            "nombre": request.form["nombre"],
            "fecha_nacimiento": request.form["fecha_nacimiento"],
            "direccion": request.form["direccion"],
            "telefono": request.form["telefono"],
            "parroquia": request.form["parroquia"],
            "sacramento": request.form["sacramento"]
        }
        estudiantes.update_one({"_id": ObjectId(id)}, {"$set": nuevo_dato})
        flash("Estudiante actualizado correctamente.", "info")
        return redirect("/consultas")

    est["_id"] = str(est["_id"])  # Convertir para usar en HTML
    return render_template("editar.html", estudiante=est)

@app.route("/ficha/<id>")
def ficha(id):
    estudiante = estudiantes.find_one({"_id": ObjectId(id)})
    if estudiante:
        estudiante["_id"] = str(estudiante["_id"])
        return render_template("ficha.html", est=estudiante)
    else:
        return "Estudiante no encontrado", 404

@app.route("/ficha_pdf/<id>")
def ficha_pdf(id):
    estudiante = estudiantes.find_one({"_id": ObjectId(id)})
    if not estudiante:
        return "Estudiante no encontrado", 404

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Logo
    logo_path = os.path.abspath(os.path.join("static", "logo.png"))

    if os.path.exists(logo_path):
        c.drawImage(logo_path, 50, height - 120, width=120, preserveAspectRatio=True)

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 80, "Ficha del Catequizado")

    # Datos del estudiante
    c.setFont("Helvetica", 12)
    y = height - 150
    c.drawString(50, y, f"Nombre: {estudiante.get('nombre', '')}")
    y -= 20
    c.drawString(50, y, f"Fecha de nacimiento: {estudiante.get('fecha_nacimiento', '')}")
    y -= 20
    c.drawString(50, y, f"Dirección: {estudiante.get('direccion', '')}")
    y -= 20
    c.drawString(50, y, f"Teléfono: {estudiante.get('telefono', '')}")
    y -= 20
    c.drawString(50, y, f"Parroquia: {estudiante.get('parroquia', '')}")
    y -= 20
    c.drawString(50, y, f"Sacramento: {estudiante.get('sacramento', '')}")

    # Espacio para firma
    y -= 60
    c.line(50, y, 250, y)
    c.drawString(50, y - 15, "Firma del Catequista")

    # Guardar y devolver
    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"ficha_{estudiante['nombre'].replace(' ', '_')}.pdf",
                     mimetype='application/pdf')
    
    
@app.route("/catequistas")
def ver_catequistas():
    lista_catequistas = list(catequistas.find())
    
    for cat in lista_catequistas:
        persona_id = cat.get("persona_id")
        if persona_id:
            persona = personas.find_one({"_id": persona_id})
            cat["nombre"] = persona.get("nombre", "Desconocido") if persona else "Desconocido"
        else:
            cat["nombre"] = "No asignado"
        
        # Por si el _id es ObjectId y lo necesitas como string para alguna funcionalidad
        cat["_id"] = str(cat["_id"])

    return render_template("catequistas.html", catequistas=lista_catequistas)



@app.route("/parroquias")
def ver_parroquias():
    parroquias_lista = list(parroquias.find())
    for p in parroquias_lista:
        p["_id"] = str(p["_id"])
    return render_template("parroquias.html", parroquias=parroquias_lista)




@app.route("/niveles")
def ver_niveles():
    niveles = list(nivelcatequesis.find())
    for n in niveles:
        n["_id"] = str(n["_id"])
    return render_template("niveles.html", niveles=niveles)


@app.route("/sacramentos")
def ver_sacramentos():
    lista = list(sacramentos.find())
    for s in lista:
        s["_id"] = str(s["_id"])
    return render_template("sacramentos.html", sacramentos=lista)

@app.route("/personas")
def ver_personas():
    personas = list(db["Personas"].find())
    for p in personas:
        p["_id"] = str(p["_id"])  # Convertir ObjectId a string
    return render_template("personas.html", personas=personas)


@app.route("/libros")
def libros_view():
    libros = list(db["Libros"].find())
    return render_template("libros.html", libros=libros)

if __name__ == "__main__":
    app.run(debug=True)
