from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "clave-super-secreta"


# Conexión a MongoDB local
client = MongoClient("mongodb://localhost:27017/")
db = client["GodsPlanDB"]
estudiantes = db["Estudiantes"]

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

    total = len(estudiantes_lista)
    parroquias = estudiantes.distinct("parroquia")

    return render_template("consultas.html",
                           estudiantes=estudiantes_lista,
                           total=total,
                           parroquias=parroquias,
                           sacramento_filtro=sacramento_filtro,
                           parroquia_filtro=parroquia_filtro)



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


if __name__ == "__main__":
    app.run(debug=True)
