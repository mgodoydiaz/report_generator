"""Este script se logea a un sitio web y obtiene el contenido html de una  página específica."""
import requests

# link para login https://www.edufacil.cl/control3.php , se hace con un post donde el cuerpo es
# cuerpo rut_usuario=18720297-3&pass=asdfG1545%26

login_url = "https://www.edufacil.cl/control3.php"
cabeceras = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.edufacil.cl",
    "Connection": "keep-alive",
}
import json
# Se carga el archivo credentials.json
with open("aux_files/credentials.json", "r", encoding="utf-8") as archivo:
    cuerpo = json.load(archivo)

#url para obtener html con la lista de un curso
#https://edufacil.cl/colegios/alumnos/configalumnos.php?offset=0&rbd=16843&clickAlertas=0&cursos=55187&anio=2025&estadomat=todos&parametro=todos&texto=

link_lista = "https://edufacil.cl/colegios/alumnos/configalumnos.php?offset=0&rbd={rbd}&clickAlertas=0&cursos={cursos}&anio={anio}&estadomat={estadomat}&parametro=todos&texto="
dic_params = {
    "rbd": 16843,
    "cursos": 55187,
    "anio": 2025,
    "estadomat": 1
}

if __name__ == "__main__":
    with requests.Session() as sesion:
        respuesta = sesion.post(login_url, headers=cabeceras, data=cuerpo)
        print(respuesta.text)  # esto imprime el html de la pagina a la que se hizo login
        # ahora se hace un get a la pagina que tiene la informacion que se quiere obtener
        # se hace un get a link_lista con los parametros en dic_params
        respuesta_lista = sesion.get(link_lista.format(**dic_params))
        # Se guarda en un archivo list_response.html
        with open("list_response.html", "w", encoding="utf-8") as archivo:
            archivo.write(respuesta_lista.text)
        print("Archivo guardado en list_response.html")

