import csv
import json

data = '''
{
"Results":
         [
         { "id": "1", "Name": "Jay" },
         { "id": "2", "Name": "Mark" },
         { "id": "3", "Name": "Jack" }
         ],
"status": ["ok"]
}
'''

with open('inventario.json') as f:
  info = json.load(f)
  # print(len(info))
  info2 = info[0]
  # print(info2)
  # print(len(info2))
# quit()
# info = json.loads(data)['Results']

# for linea in info:
lf=[]
for linea in info:
  del linea["block_at_file"]
  del linea["block_lin_nro"]
  del linea["interprets"]
  cntq = len(linea["queries"])
  if cntq > 1:
    print(cntq)
  # print(linea["block_name"])
  # lf.append(linea["block_name"])
  # lf.append(linea["queries"])
  print(linea)


print(lf)

# Escribir csv
with open("samplecsv.csv", 'w') as f:
    wr = csv.DictWriter(f, fieldnames = info[1].keys())
    wr.writeheader()
    wr.writerows(info)
