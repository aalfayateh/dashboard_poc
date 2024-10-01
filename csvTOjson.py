import csv
import json

# Nombre del archivo CSV de entrada
csv_file = 'C:\\Users\\dmurias\\Downloads\\eventosMurcia_v1.csv'
# Nombre del archivo JSON de salida
json_file = 'C:\\Users\\dmurias\\Downloads\\eventosMurcia.json'

# Inicializar la estructura del JSON
data = {
    "table": "Ruta",
    "rows": []
}

# Leer el archivo CSV y convertirlo a JSON
with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file, delimiter='\t')  # Utiliza tabulaciones como delimitador
    for row in reader:
        # Agregar cada fila al JSON
        data['rows'].append({
            "TipoEvento": int(row['TipoEvento']),
            "Latitud": float(row['Latitud']),
            "Longitud": float(row['Longitud']),
            "Fecha": int(row['Fecha'])
        })

# Guardar el resultado en un archivo JSON
with open(json_file, mode='w', encoding='utf-8') as file:
    json.dump(data, file, indent=4)

print(f'El archivo JSON ha sido creado: {json_file}')
