1. Repository-Liste aktualisieren und Universe sicherstellen:

`sudo add-apt-repository universe`<br>
`sudo apt update`

2. Benötigte Pakete holen:

`sudo apt install python3.12-venv python3-pip`

(falls python3-pip nicht gefunden wird, nimm sudo apt install python3-pip --reinstall)

3. Venv erstellen + aktivieren (achte auf activate, nicht active):

`python3 -m venv .venv` <br>
`source .venv/bin/activate`

4. Requirements installieren:

`pip install -r requirements.txt` <br>
`pip install -r requirements_frontend.txt`

Danach kannst du mit den Konfigurations- und Startschritten weitermachen.






1. Ollama (fertiges Docker-Image verwenden):

`apptainer pull ollama.sif docker://ollama/ollama`

2. Milvus 2.5.2:

`apptainer build milvus.v2.5.2.sif docker://milvusdb/milvus:v2.5.2`

(falls nötig mit --fakeroot laufen lassen; die Config-Dateien liegen unter milvus_configs/ und werden später nur gemountet.)

3. FastAPI-Container (eigene Definition):

`apptainer build fastapi_container.sif container_recipes/fastapi_recipe.def`

4. Redis:

`apptainer build redis.sif container_recipes/redis.def`

5. Gradio-Frontend:

`apptainer build gradio.sif container_recipes/gradio.def`