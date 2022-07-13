import json

with open('inventario.json') as f:
    data = json.load(f)
for item in data:
    print(item["block_name"])
    print(len(item["interprets"][0]["blocks_usados"]),
          item["interprets"][0]["blocks_usados"])
    # print(item["interprets"][0]["blocks_usados"])
    print(len(item["queries"]), item["queries"])
    # print(item["queries"])
    # [0].interprets[0].blocks_usados
    # [0].interprets
    print()


# Método indicando cada posicion con su índice
# print(data[0]["block_at_file"])
# print(data[0]["block_name"])
# print(data[0]["queries"])
