# MiPresupuesto

Aplicación web de finanzas personales hecha solo con Python y Streamlit. No usa IA, APIs externas ni servicios de pago.
Montos en soles peruanos (S/).

## Funciones
Panel con indicadores y gráficos · Mis ingresos · Mis gastos · Mi presupuesto (semáforo verde/amarillo/rojo) ·
Historial con filtros · Mis estadísticas · Mis ahorros · Exportación a CSV, Excel y PDF mensual · Copia de seguridad.
Todo se puede agregar, editar y eliminar (con confirmación al eliminar).

## Archivos
```
app.py          Interfaz y páginas
database.py     SQLite (ingresos, gastos, presupuestos, metas)
reportes.py     CSV, Excel y PDF
requirements.txt
.streamlit/config.toml   Tema azul, blanco y verde suave
```

## Ejecutar en tu computadora
```
pip install -r requirements.txt
streamlit run app.py
```
Los datos se guardan en `data/mipresupuesto.db` (se crea sola).

## Publicar en Streamlit Community Cloud
1. Sube estos archivos a un repositorio de GitHub (`app.py` en la raíz).
2. En https://share.streamlit.io elige **Create app**, selecciona el repositorio, la rama y `app.py`.
3. Pulsa **Deploy**. No necesita secretos.

## Limitación importante: almacenamiento efímero
Streamlit Community Cloud puede borrar los archivos locales (incluida la base SQLite) al reiniciar,
redesplegar o tras un periodo de inactividad. Además, **todos los visitantes de la misma app comparten la misma base de datos**.
Por eso:
- Descarga la copia de seguridad (.db) en «Exportar y copia» con regularidad y restáurala cuando sea necesario.
- Para uso personal, mantén la app privada (Settings > Sharing) o ejecútala en tu computadora.

## Notas
- El presupuesto (límite total y por categoría) se aplica a todos los meses.
- Los ahorros son independientes: no modifican el saldo disponible.
- El PDF usa la fuente estándar: los acentos y la ñ salen bien, pero otros símbolos (por ejemplo emojis) se reemplazan por «?».
