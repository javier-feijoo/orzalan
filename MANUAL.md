# Manual de ayuda ORZALAN

## 1. Inicio rápido

1. Ejecuta la aplicación.
2. En **Configuración** completa los datos básicos de la empresa y, si quieres, el logo.
3. Revisa el **Catálogo** base (productos y categorías).
4. Crea clientes en **Clientes**.
5. Crea presupuestos en **Presupuestos**.

## 2. Catálogo

### 2.1 Productos
- **Referencia**: identificador único del producto.
- **Nombre** y **Unidad**: lo que verá el alumno/cliente.
- **Coste, margen y precio de venta**: si el precio no es fijo, se calcula a partir del margen.
- **Activo / inactivo**: controla si el producto se muestra en selección.

### 2.2 Categorías
- Cada categoría tiene **código** y **nombre** (útil para importar/exportar).
- “Sin categoría” es la categoría por defecto y no se puede eliminar.

## 3. Clientes

- Crea, edita y elimina clientes.
- Los presupuestos quedan asociados al cliente seleccionado.

## 4. Presupuestos

### 4.1 Cabecera
- **Número**: se genera automáticamente, pero puedes cambiarlo.
- **Cliente**: selecciona el cliente al que va dirigido.
- **Fecha y validez**: controla la vigencia del presupuesto.
- **IVA y descuento global**: afectan a todas las líneas.

### 4.2 Líneas
- **Añadir desde catálogo**: guarda un **snapshot** (referencia, descripción, unidad y precio).
- **Añadir línea libre**: útil para conceptos puntuales.
- Puedes editar **cantidad**, **descuento** e **IVA** por línea.

### 4.3 Totales
- Se calculan en tiempo real: **subtotal**, **IVA total** y **total final**.

## 5. Importar / Exportar

### 5.1 Catálogo
- Importar CSV/XLSX con mapeo de columnas (autodetección si los nombres coinciden).
- Exportar plantilla con datos actuales para usar como base.

### 5.2 Categorías
- Importar y exportar en CSV/XLSX.

## 6. Herramientas de reinicio

En **Herramientas**:
- **Reiniciar catálogo (base)**: borra catálogo y categorías y carga `assets/catalogo_base.csv`.
- **Reiniciar catálogo (vacío)**: deja solo “Sin categoría”.
- **Reinicio total (base/vacío)**: además borra clientes, presupuestos y limpia datos de empresa.

## 7. Exportación de presupuestos

- **PDF**: con logo y datos de empresa si existen.
- **XLSX**: incluye logo y totales.

## 8. Archivos importantes

- `data/empresa.json`: configuración de empresa.
- `assets/catalogo_base.csv`: catálogo base para primera ejecución.
- `exports/`: archivos exportados.
- `exports/`: archivos exportados.
## 9. Flujo recomendado

1. **Configura la empresa**: revisa datos y logo en **Configuración**.
2. **Revisa el catálogo base**: ajusta categorías y productos si es necesario.
3. **Crea clientes**: añade los datos mínimos antes de presupuestar.
4. **Crea un presupuesto**:
   - Selecciona cliente.
   - Añade líneas desde catálogo.
   - Ajusta cantidades, descuentos e IVA.
5. **Revisa totales** y guarda.
6. **Exporta** en PDF o XLSX.

Si quieres empezar desde cero, usa **Herramientas > Reinicio total (base/vacío)**.

## 10. Ejemplo real: instalación de red en aula

**Contexto**: aula con 12 puestos. Se requiere cableado estructurado, canalizaciones, rack mural y electrónica activa básica.

1. **Cliente**: crea “IES Ejemplo - Aula 2”.
2. **Presupuesto**: crea uno nuevo.
3. **Líneas desde catálogo** (con referencias reales y precios de catálogo):

| Ref | Concepto | Cantidad | Precio venta | Subtotal |
| --- | --- | --- | --- | --- |
| CAB-0010 | Cable Cat6 U/UTP LSZH 305 m | 1 bobina | 100.62 | 100.62 |
| CAN-0003 | Canaleta PVC 40x20 (tramo 2 m) | 15 ud | 3.36 | 50.40 |
| CON-0003 | Keystone RJ45 Cat6 UTP | 12 ud | 1.88 | 22.56 |
| CON-0010 | Placa empotrable 2x keystone | 6 ud | 3.72 | 22.32 |
| CON-0023 | Patch panel 19" 24 puertos Cat6 | 1 ud | 47.52 | 47.52 |
| RAC-0018 | Rack mural 19" 9U 600x450 | 1 ud | 134.94 | 134.94 |
| NET-0004 | Switch Gigabit no gestionado 24 puertos | 1 ud | 74.40 | 74.40 |
| ENE-0002 | PDU 19" 1U 8 Schuko | 1 ud | 24.30 | 24.30 |
| CAB-0056 | Latiguillo Cat6 UTP 1 m | 14 ud | 1.49 | 20.86 |
| SRV-0003 | Certificación punto de red (por punto) | 12 ud | 10.20 | 122.40 |
| SRV-0005 | Documentación y etiquetado (por punto) | 12 ud | 2.55 | 30.60 |

**Total orientativo (sin IVA): 650.92**

4. **Ajusta cantidades** y revisa IVA/desc.
5. **Exporta** el PDF para entregar al alumno o cliente.

Este ejemplo puede repetirse variando el número de puntos o el tipo de equipamiento.
