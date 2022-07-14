#!/usr/bin/env python3
######################################################################
# Programa   : analizar_lua.py                                       #
# Descripción: Script que realiza estas acciones:                    #
#                                                                    #
#               1) Genera un inventario JSON de un archivo .lua.ter  #
#               registrando sus bloques y sus correspondientes       #
#               interpretes y bloques llamados desde cada uno        #
#                                                                    #
#               2) Con el inventario ya armado genera un gráfico en  #
#               archivos .dot (lenguaje gráfico) y en formato .png   #
#               representando la relación "bloque"->"bloque llamado" #
#               Si te invoca el script con el parámetro '-l' solo    #
#               grafica relaciones entre bloques locales del Dominio #
#               Por defecto grafica relaciones entre bloques locales #
#               y externos.                                          #
#                                                                    #
#               3) Con el parámetro '-m' en la línea de comando      #
#               pueden definirse bloques a marcar en otro color      #
#               en el grafo general.                                 #
#                                                                    #
#               4) Con el parámetro '-r' puede genearse un subgrafo  #
#               con el camino inverso de bloques desde el bloque     #
#               especificado.                                        #
#                                                                    #
#               5) Ver 'python3 analizar_lua.py --help' para ver     #
#               lista y formato de parámetros                        #
#                                                                    #
#Argumentos:                                                         #
#  -h, --help            show this help message and exit             #
#  -i INPUT_FILE, --input-file INPUT_FILE                            #
#                        Archivo lua.ter a leer.                     #
#  -g, --graph           Graficar relación                           #
#                        Bloque_A->llama a-> Bloque_B                #
#  -l, --local-blocks    Graficar solo bloques locales del Dominio.  #
#                        Sino se define grafica Locales y Externos   #
#  -m [MARK_BLOCKS], --mark-blocks [MARK_BLOCKS]                     #
#                        Bloque/s a marcar en grafo                  #
#                        (BLOQUE o BLOQUE1,BLOQUE2,etc...).          #
#                        Para múltples bloques separar con comas.    #
#  -r REVERSE_PATH_BLOCK, --reverse-path-block REVERSE_PATH_BLOCK    #
#                        Bloque origen del camino inverso.           #
#  -d, --debug           Imprimir Log DEBUG                          #
#                                                                    #
# Versión    : 1.2.0                                                 #
# Autor      : Sergio Vigo                                           #
# Email      : svigo@huenei.com                                      #
######################################################################
import os
import sys
import re
import pprint as pp
import json
import copy
from collections import OrderedDict
import logging
import pygraphviz as pgv
import networkx as nx
from networkx.drawing.nx_pydot import read_dot, write_dot
import argparse

# Librería para debugging
import pdb



class InventarioTerrierFile():


    def __init__(self, archi, graficar, ver_bloq_locales, marcar, bloq_reverse_path ,debug=False):
        '''
        debug (boolean) -> activa o no los mensajes de logging en la pantalla
        '''
        self.n_archi = archi
        self.graficar = graficar
        self.ver_bloq_locales = ver_bloq_locales
        self.marcar = marcar
        self.bloq_reverse_path = bloq_reverse_path
        self.debug = debug

        # Nombre del lua.ter sin path
        basename = os.path.basename(self.n_archi)
        self.file_name = os.path.splitext(basename)[0]

        ###############################
        # regex de estructuras terrier
        ###############################

        self.block = re.compile(r'block\s*\(.*\)\s*\"Español\"\s*[\s\S]*?\)')

        self.blk_name = re.compile(r'([A-Z0-9]\w+\([\s\S]*?\))')

        self.interpret = re.compile(r'interpret\s*{([\s\S]*)?}\s*as\s*{[\s\S]*};',re.MULTILINE)

        self.tests = re.compile(r'tests\s*=\s*{\s*({[\s\S]*]]\s*})\s*};',re.MULTILINE)
        # re.compile(r'tests\s*=\s*{[\s\S]*?};',re.MULTILINE)

        self.tests_line = re.compile(r'tests\s*=\s*',re.MULTILINE)
        self.tests_end = re.compile(r'};',re.MULTILINE)

        self.testcase_end  = re.compile(r']]\s*}', re.MULTILINE)

        self.delta_request_info = re.compile(r'delta_request_info')

        # Estructuras de almacenamiento
        self.texto_int = ''
        self.inventario = []
        self.block_data = {}
        self.interpret_data = {}
        self.tests_data = []
        self.testcase = {}
        self.testscases = {}
        self.sen = False

        # Setting del Logging
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
        if self.debug == False:
            logging.disable(logging.DEBUG)

        # Inventariar bloques e interprets
        self.inventariar()

        # Si se agregó parámetro -g
        if self.graficar:
            self.graficar_relaciones(
                self.ver_bloq_locales,
                self.marcar,
                self.bloq_reverse_path
            )

    def inventariar(self):
        ''' Lectura y procesado del archivo lua.ter  '''

        logging.info(f'✓ Creando inventario de {self.n_archi}.')
        with open(self.n_archi,'r') as archivo:
            linea = archivo.readline()
            cont_lin = 0
            while linea:

                plin = linea
                logging.debug('>>> ' + plin)
                cont_lin = cont_lin + 1
                if self.block.search(plin) != None:

                    if self.sen == True :
                        # Se guarda lína de finalización de bloque anterior
                        # línea de nvo. bloque -1
                        #MARK Si hay commentarios quedan en el bloque anterior las líneas
                        ln_end_block = cont_lin - 1
                        self.block_data['block_lin_nro']['end'] = ln_end_block

                        blk_dict = copy.deepcopy(self.block_data)
                        logging.debug('✓ Bloque encontrado')
                        self.inventario.append(blk_dict)

                        self.block_data = {}
                        self.interpret_data = {}
                        self.tests_data = []
                        self.testcase = {}
                        self.testscases = {}

                        self.block_data.clear()
                        self.interpret_data.clear()
                        self.tests_data.clear()
                        self.testscases.clear()
                        self.sen = False

                    sent_blk = self.block.search(plin)
                    #logging.info('Bloque Sentencia: ' + sent_blk.group())
                    nom_blk = self.blk_name.search(sent_blk.group())
                    logging.debug('[Bloque Nombre]:\t' + nom_blk.group())

                    self.block_data['block_name'] = nom_blk.group()
                    self.block_data['block_at_file'] = self.n_archi

                    self.block_data['block_lin_nro']= {}
                    self.block_data['block_lin_nro']['start'] = cont_lin

                    self.block_data['interprets'] = list()
                    self.block_data['queries'] = list()

                    self.sen = True
                    #cont = 0


                # Detección y guardado de queries ejemplo del bloque
                if '--&' in plin:
                    query = plin.strip()[4:]
                    self.block_data['queries'].append(query)


                #TODO Mejorar la busqueda del 'interpret' para evitar falsos positivos en comentarios
                if ('interpret' in plin) and (not plin.startswith('--')) and (plin.lstrip().startswith('interpret')):

                    logging.debug('✓ Entró en interpret')
                    self.texto_int = self.texto_int + plin
                    logging.debug(' Buscando todo el interpret...')
                    while True:

                        linea = ''
                        linea = archivo.readline()
                        plin = linea
                        cont_lin = cont_lin + 1
                        self.texto_int = self.texto_int + plin
                        logging.debug(f'Linea <{cont_lin}>  {self.texto_int}')
                        if self.interpret.search(self.texto_int) != None:
                            break

                    # Busca string "todo" el interpret
                    int_sent = self.interpret.search(self.texto_int)
                    logging.debug('✓ Registrando interpret')
                    #print(self.block_data['interprets'])

                    # Guardo todo el interpret encontrado ( {}as{}; )
                    self.interpret_data['raw_string'] = int_sent.group()

                    # Guardo la expresión terrier antes del 'as'
                    self.interpret_data['terrier_expr'] = int_sent.group(1)

                    # Guardo los nombres de bloques ( NOMBRE() ) que hay en la expresión terrier
                    #interpret_data['blocks_usados'] = [ elem[0] for elem in blk_name.findall(self.texto_int)]
                    self.interpret_data['blocks_usados'] = list(OrderedDict.fromkeys([ elem for elem in self.blk_name.findall(self.texto_int)]))

                    # Almaceno el interpret encontrado en la lista de interpret del bloque al que pertenece
                    self.block_data['interprets'].append(self.interpret_data)

                    logging.debug('✓ Encontrado interpret!')
                    logging.debug('-----------------------------')
                    logging.debug(f'\t{int_sent.group()}')
                    logging.debug('-----------------------------')
                    logging.debug(f'\t\t{int_sent.group(1)}')
                    self.texto_int = ''
                    self.interpret_data = {}

                # Lee nueva linea del archivo
                linea = archivo.readline()


        # Se registra ln de finalización del bloque (linea bloque nuevo -1)
        # Se graba el último bloque que queda sin grabar
        ln_end_block = cont_lin
        self.block_data['block_lin_nro']['end'] = ln_end_block
        self.inventario.append(self.block_data)
        self.block_data= {}


    def mostrar(self):
        ''' Imprime el inventario json '''
        inventario_json = json.dumps(self.inventario)
        pp.pprint(inventario_json)


    def to_file(self):
        ''' Graba el inventario de bloques en formato JSON '''
        nombre_inventario = self.n_archi + '_inventario.json'
        with open( nombre_inventario, 'w') as fp:
            json.dump(self.inventario, fp, indent=4, ensure_ascii=False, separators=(',', ': '), sort_keys=True)
        logging.info('✓ Inventario de bloques bajado a JSON.')
        logging.info(f'    * Archivo: {nombre_inventario}')


    def implrimir_blocks(self):
        ''' Imprime los bloques "locales" '''
        for elem in self.inventario:
            print(elem['block_name'])


    def bloques_locales(self):
        '''Retorna lista de bloques "locales" '''
        return [elem['block_name'] for elem in self.inventario]


    def graficar_relaciones(self, ver_bloq_locales=False, marcar="", bloque_origen=""):
        '''
        Genera un gráfico de la relación bloque -> bloques llamados dentro de él
        Puede recibir un nombre de bloque o una lista de nombres de bloque a
        buscar y marcar con otro color.
        Los nombres deben ser en mayúsculas, sin (), ni parámetros.

        Argumentos:
           * ver_bloq_locales (boolean) -> True: grafica solo relaciones de bloques locales.
                                        -> False: grafica relaciones de bloques locales y externos.
           * marcar (str) -> string con los nombres de los bloques a marcar.

           * bloque_origen (str) -> nombre del bloque desde dónde se
             inicial el camino inverso. Si se deja vacío no se grafica.
        '''

        bloques_a_marcar = []
        file_name_sufijo = ""

        # Se arma la lista a buscar con uno o varios bloques
        lista_marcar = marcar.split(',')
        bloques_a_marcar = [elem+'(...)' for elem in lista_marcar]

        if bloque_origen != "":
            bloque_origen = bloque_origen + '(...)'

        # Se normalizan los nombres de los bloques locales quitándoles los parámetros
        bloques_locales = [re.sub("\(.*\)", '(...)', elem) for elem in self.bloques_locales()]

        logging.debug('✓ Bloques locales:')
        logging.debug(f'  * {bloques_locales}')

        G = pgv.AGraph(directed = True, rankdir="LR", ranksep=8.0, id="mi_luar_ter", name="mi_lua_ter")
        # Atributos del gráfico
        #G.graph_attr["size"] = 16.6
        G.graph_attr["sep"] = "7"
        G.graph_attr["esep"] = "5"

        # Atributos de nodo
        G.node_attr["shape"] = "box"
        G.node_attr["color"] = "goldenrod"
        G.node_attr["style"] = "rounded, filled"

        for elem in self.inventario:
            for interpret in elem["interprets"]:
                # Normalizado de campos para representar en Dot (bloques sin parámetros)
                elemento = elem["block_name"].replace("\n","")
                elemento = re.sub('\s+', ' ', elemento)
                elemento = re.sub('\"', '\'', elemento)
                elemento = re.sub("\(.*\)", '(...)', elemento)

                logging.debug(f'✓ Bloque: {elemento}')
                #G.add_node(elemento)
                for bloque in interpret["blocks_usados"]:
                    # Normalizado de campos para representar en Dot (bloques sin parámetros)
                    bloque = bloque.replace("\n", "")
                    bloque = re.sub('\s+', ' ', bloque)
                    bloque = re.sub('\"', '\'', bloque)
                    bloque = re.sub("\(.*\)", '(...)', bloque)

                    logging.debug(f'✓    Relación {elemento} -> {bloque} ')
                    # Agrega la relación entre bloques
                    if ver_bloq_locales:
                        file_name_sufijo = "_locales"
                        if bloque in bloques_locales or bloque =="PHONE_NUMBER(...)": # PHONE_NUMBER() es un extended block de SH
                           G.add_edge(elemento, bloque)
                           # Si bloque está en bloques_a_marcar lo pinta de verde
                           if  bloque in bloques_a_marcar:
                               n = G.get_node(bloque)
                               n.attr["fillcolor"] = "green"

                           if  elemento in bloques_a_marcar:
                               n = G.get_node(elemento)
                               n.attr["fillcolor"] = "green"

                    else:
                        file_name_sufijo = "_todos"
                        G.add_edge(elemento, bloque)
                        # Si bloque está en bloques_a_marcar lo pinta de verde
                        if  bloque in bloques_a_marcar:
                            n = G.get_node(bloque)
                            n.attr["fillcolor"] = "green"

                        if  elemento in bloques_a_marcar:
                               n = G.get_node(elemento)
                               n.attr["fillcolor"] = "green"

        logging.info('✓ Graficando.')

        # *** Gráfico General ***

        # Genera archivo lenguaje dot
        g_dot_file = self.file_name + file_name_sufijo + ".gv"
        G.write(g_dot_file)

        # Genera archivo png
        g_png_file = self.file_name + file_name_sufijo +".png"
        G.layout(prog='dot')
        G.draw(g_png_file)
        logging.info('✓ Gráfico general generado.')
        logging.info(f'    * Archivo: {g_dot_file}')
        logging.info(f'    * Archivo: {g_png_file}')


        if bloque_origen != "":

            # *** Gráfico camino inverso ***
            assert G.get_node(bloque_origen) != None, "Bloque inexistente"

            # Genera gráfico dot de camino inverso desde un nodo = bloque
            G_inv=self._camino_inverso(G, bloque_origen)

            # Genera archivo lenguaje dot
            g_inv_dot_file = self.file_name + "_camino_inv_" + bloque_origen[:-5] + ".gv"
            G_inv.write(g_inv_dot_file)

            # Genera archivo png
            g_inv_png_file = self.file_name + "_camino_inv_" + bloque_origen[:-5] + ".png"
            G_inv.layout(prog='dot')
            G_inv.draw(g_inv_png_file)
            g_inv_svg_file = self.file_name + "_camino_inv_" + bloque_origen[:-5] + ".svg"
            G_inv.draw(g_inv_svg_file)
            logging.info(f'✓ Gráfico camino inverso generado desde: {bloque_origen}')
            logging.info(f'    * Archivo: {g_inv_dot_file}')
            logging.info(f'    * Archivo: {g_inv_png_file}')
            logging.info(f'    * Archivo: {g_inv_svg_file}')

    def _camino_inverso(self, G_total, bloque_orig):

        # Constructor de Networkx que lee un Graphviz-dot
        G= nx.DiGraph(G_total)

        # Lista de aristas (relaciones entre nodos) desde el bloque_orig
        upstream_lst = list(nx.edge_dfs(G, bloque_orig, orientation='reverse'))
        #print(upstream_lst)

        # Normalización de las tuplas del reverse
        GM=[]
        for elem in upstream_lst:
            GM.append((elem[0], elem[1]))

        #print(GM)

        #Lista de tuplas de aristas a grafo nx
        NG =nx.DiGraph(GM)

        # Grafo nx a Graphviz dot para colocar atributos
        NG_gv =nx.nx_agraph.to_agraph(NG)

        # Atributos del gráfico Graphviz
        #NG_gv.graph_attr["size"] = 16.6
        NG_gv.graph_attr["id"] = "camino_reverso"
        NG_gv.graph_attr["sep"] = "7"
        NG_gv.graph_attr["esep"] = "5"
        NG_gv.graph_attr["rankdir"] = "LR"
        NG_gv.graph_attr["ranksep"] = "8.0"
        NG_gv.graph_attr["directed"] = True

        # Atributos de nodos Graphviz
        NG_gv.node_attr["shape"] = "box"
        NG_gv.node_attr["color"] = "goldenrod"
        NG_gv.node_attr["style"] = "rounded, filled"

        # Nodo origen del camino inverso a resaltar
        n=NG_gv.get_node(bloque_orig)
        n.attr["fillcolor"] = " green"

        return NG_gv  # Retorno el Graphviz-dot del camino inverso


if __name__ == '__main__':

    # argparse
    # https://ellibrodepython.com/python-argparse
    #parser.add_argument('-o', '--operacion',
    #                type=str,
    #                choices=['suma', 'resta', 'multiplicacion'],
    #                default='suma', required=False,
    #                help='Operación a realizar con a y b')

    parser = argparse.ArgumentParser(description="Inventario de bloques lua.ter y grafos de relaciones.")
    parser.add_argument("-i", "--input-file", required=True, help="Archivo lua.ter a leer.")
    parser.add_argument("-g", "--graph", action="store_true", default=False, required=False, help="Graficar relación Bloque_A->llama a-> Bloque_B")
    parser.add_argument("-l", "--local-blocks", action="store_true", default=False, required=False,
        help="Graficar solo bloques locales del Dominio. Sino se define grafica Locales y Externos")
    parser.add_argument("-m", "--mark-blocks", nargs="?", type=str, default="", required=False,
         help="Bloque/s a marcar en grafo (BLOQUE o BLOQUE1,BLOQUE2,etc...). Para múltples bloques separar con comas.")
    parser.add_argument("-r", "--reverse-path-block", type=str, default='', required=False, help="Bloque origen del camino inverso.")
    parser.add_argument("-d", "--debug", action="store_true", required=False, help="Imprimir Log DEBUG")

    # Se convierte los parser_args en un Dict()
    args = vars(parser.parse_args())

    # Tiene que llamarse a -g para graficar antes de definir bloques a marcar o bloque->camino inverso
    if (args['graph'] == False) and (args['local_blocks'] == True):
        parser.error('El argumento --local-blocks requiere del argumento --graph para generar el Grafo antes.')
    if (args['graph'] == False) and (args['mark_blocks'] != ''):
        parser.error('El argumento --mark-blocks requiere del argumento --graph para generar el Grafo antes.')
    if (args['graph'] == False) and (args['reverse_path_block'] != ''):
        parser.error('El argumento --reverser-path-block requiere del argumento --graph para generar el Grafo antes.')

    #print(args)

    tf = InventarioTerrierFile(
        archi=args['input_file'],
        graficar=args['graph'],
        ver_bloq_locales=args['local_blocks'],
        marcar=args['mark_blocks'],
        bloq_reverse_path=args['reverse_path_block'],
        debug=False)

    # Bajada del inventario a JSON
    tf.to_file()

    # Listado de bloques locales por pantalla
    #tf.listar_blocks()

