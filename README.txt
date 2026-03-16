
Guía paso a paso

1️⃣ Instalar Python 3.11

2️⃣ Crear bot en Telegram con BotFather y copiar TOKEN

3️⃣ Editar bot.py:
- TOKEN = "TU_TOKEN"
- CHANNEL_STORAGE = "@canal_almacenamiento"
- CHANNEL_CATALOG = "@canal_catalogo"

4️⃣ Instalar dependencias:
pip install -r requirements.txt

5️⃣ Ejecutar el bot:
python bot.py

6️⃣ Flujo de subida:
/subir -> nombre -> imagen -> archivos -> /ok
El bot guardará archivos en canal de almacenamiento y publicará automáticamente en canal catálogo con botón START.

7️⃣ Usuarios podrán tocar START y recibir los archivos al privado.
