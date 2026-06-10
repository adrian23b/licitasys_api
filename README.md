# LicitaSys

LicitaSys es un proyecto diseñado para gestionar y automatizar procesos de licitaciones. Este sistema facilita la administración de licitaciones, la presentación de propuestas y la evaluación de ofertas.

## Características principales

- **Gestión de licitaciones:** Creación, edición y seguimiento de licitaciones.
- **Presentación de propuestas:** Plataforma para que los proveedores presenten sus propuestas.
- **Evaluación de ofertas:** Herramientas para evaluar y comparar las propuestas recibidas.
- **Seguridad y acceso:** Control de acceso y roles para garantizar la seguridad de la información.

## Requisitos del sistema

- Python 3.8 o superior
- PostgreSQL 13 o superior
- Docker (opcional para despliegue)

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu_usuario/licitasys.git
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura la base de datos:
   ```bash
   python manage.py migrate
   ```
4. Inicia el servidor:
   ```bash
   python manage.py runserver
   ```

## Documentación

- [Especificaciones](doc/especificaciones.md): propósito, módulos, arquitectura, flujo de datos y dependencias externas.
- [API](doc/api.md): endpoints de salud, identidad, oportunidades y crawler.
- [Modelo de datos](doc/modelo-datos.md): tablas SQLAlchemy, campos, índices, restricciones y migraciones.
- [Configuración y despliegue](doc/configuracion-despliegue.md): variables de entorno, Docker Compose, Fly.io y notas de seguridad.

## Contribución

Si deseas contribuir al proyecto, por favor sigue los siguientes pasos:

1. Haz un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`).
3. Haz tus cambios y haz commit (`git commit -am 'Añade nueva funcionalidad'`).
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`).
5. Abre un Pull Request.

## Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.