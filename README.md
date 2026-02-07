# ORZALAN

Aplicación de presupuestos y catálogo para formación en redes, creada en Python con PySide6.

Repositorio: `https://github.com/javier-feijoo/ORZALAN`

Manual de ayuda: `MANUAL.md`

## Requisitos

- Python 3.12
- Entorno virtual recomendado

## Ejecutar en desarrollo

1. Crea y activa un entorno virtual.
2. Instala dependencias: `pip install -r requirements.txt`
3. Ejecuta: `python main.py`

La app crea carpetas portables al lado del ejecutable:
`data/`, `imports/`, `exports/`, `backups/`.

## Configuracion

En Configuracion puedes:
- Definir datos de empresa y logo.
- Cambiar idioma (castellano o galego).
- Elegir tema claro u oscuro.
- Activar o ocultar costes.

## Datos y distribucion

- La configuración se guarda en `data/empresa.json`.
- En distribución se recomienda **no incluir** `data/` para que la app arranque limpia.
- Si existe `assets/catalogo_base.csv`, el catálogo base se carga automáticamente en el primer arranque.
- El logo por defecto es `assets/logo_orzalan.png` (si no hay logo configurado).

## Herramientas

En el menú **Herramientas** puedes:
- Importar y exportar catálogo.
- Importar y exportar categorías.
- Reiniciar catálogo (base o vacío).
- Reinicio total (base o vacío) con limpieza de clientes, presupuestos y empresa.

## Exportacion

- PDF: incluye logo y datos de empresa si existen.
- XLSX: incluye logo, totales y formato numerico.

## Builds (PyInstaller)

La app usa rutas relativas al ejecutable en modo portable (ver `paths.py`), por lo que `data/`, `exports/` y `backups/` se crean junto al binario.

### Windows

```powershell
scripts\\build_windows.ps1
```

### Linux

```bash
./scripts/build_linux.sh
```

El build se genera en `dist/`.

## Estructura

- `main.py`: punto de entrada.
- `paths.py`: rutas en modo portable.
- `settings.py`: configuracion en JSON.
- `ui/main_window.py`: ventana principal.
- `assets/styles.qss`: estilos base QSS.
- `assets/catalogo_base.csv`: catálogo base para primera ejecución.

## Créditos

Javier Feijóo López - Docente Informática

## Licencia

Creative Commons BY-NC-SA 4.0. Ver `LICENSE`.
