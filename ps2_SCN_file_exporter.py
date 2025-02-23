"""
Скрипт экспортирует 3D модели из демо версии игры Smesh Cars для PS2
Экспортирует с багами. Не может экспортировать карты. Надо что-то пофиксить.
"""
import bpy
from struct import *

FILE_PATH = "M:\\Недетские гонки +1000\\НЕДЕТСКИЕ ГОНКИ ПС2\\SC_Prototype_Nov_9_2002\\SMASHCAR\\SCNDATA\CUBA.SCN"
SCN_FILE_SIGNATURE = 0x53434E42

def read_char(fb):
    data = fb.read(1)
    if data == b'' or len(data) != 1:
        return None
    return unpack("B", data)[0]

def read_uint(fb):
    data = fb.read(4)
    if data == b'' or len(data) != 4:
        return None
    return unpack("I", data)[0]

def read_ushort(fb):
    data = fb.read(2)
    if data == b'' or len(data) != 2:
        return None
    return unpack("H", data)[0]

def read_string(fb):
    str = b''
    while True:
        c = fb.read(1)
        if c == b'\0' or c == b'':
            return str.decode('cp437')
        else:
            str += c
            

class MESHMod(object):
    def __init__(self):
        self.name = None
        self.is_blank_mesh = True
        self.start = None
        self.end = None
        self.vertex_list = []
        self.face_list = []
        

class SCNFileParser(object):
    def __init__(self, file_path):
        self.fb = None
        self.file_path = file_path
        
        self.mesh_start_address = None
        self.total_mesh_count = None
        self.mesh_list = []
        self.mesh_chunk_address_list = []
        
    def parse_file(self):
        self.init_file()        
        try:
            signa = read_uint(self.fb)
            # проверяем правильногсть сигнатуры и является ли файл .sb файлом 
            if signa != SCN_FILE_SIGNATURE and self.file_path[-3:] == ".SCN":
                # raise RuntimeError("Invalid file signature: %08d" % (magic))
                raise RuntimeError("Неверная сигнатура файла: %08d. Либо выбран не тот файл." % (signa))
            self.parse_file_headers()
            self.collect_mesh_chunk_addresses()
            self.parse_mesh()
        except Exception as ex:
            print(self.file_cursor)
            raise ex
        finally:
            self.fb.close()
            
    def init_file(self):
        self.fb = open(self.file_path, "rb")
               
    def parse_file_headers(self):
        # пропустим 4 байта
        self.fb.read(4)
        # берем стартовый адрес и добавим в список адресов
        self.mesh_chunk_address_list.append(read_uint(self.fb))
        # берем кол-во мешей. UPD: сомнительно считать по значению в начале файла, ибо почему-то в COLA.SCN указаны 3 меша, а их по адресам 4. Но при этомв файле CUBA.SCN все правильно и числа соответсвуют.
        # self.total_mesh_count = read_uint(self.fb) + 1
    
    def collect_mesh_chunk_addresses(self):
        # Опытным путем найдено, что каждый меш имеет 3 адреса на следующие меши.
        # Адреса находятся на смещении от начала меша. А именно start_chunk + 40h
        # Создадим контрольный список новых адресов. Если список будет пуст, значит найдены все адреса и цикл прервется.
        # Положим стартовый адрес в список. С него будем начинать поиск.
        new_addres_list = [self.mesh_chunk_address_list[0]]
        while new_addres_list:
            # берем адреса из списка
            next_adr = new_addres_list.pop()
            # переместимся к мешу и сместимся к списку следующих мешей
            self.fb.seek(next_adr + 0x40)
            # соберем адреса
            for new_adr in range(3):
                new_adr = read_uint(self.fb)
                if new_adr == 0:
                    continue
                # если адреса нет в списке
                if new_adr not in self.mesh_chunk_address_list:
                    # то положим его в общий список
                    self.mesh_chunk_address_list.append(new_adr)
                    # и в контрольный список, ибо по этому адресу надо будет пройти и собрать следующие адреса
                    new_addres_list.append(new_adr)
        
    def parse_mesh(self):
        mesh = MESHMod()
        # возьмем адрес меша из списка адресов
        start_addr = self.mesh_chunk_address_list.pop()
        # в теории, посмотрев все файлы, они устроены с определенным смещением от адреса меша
        # получим имя меша start + 18h
        self.fb.seek(start_addr + 0x18)
        mesh.name = read_string(self.fb)
        # адрес вершин start + E4h
        self.fb.seek(start_addr + 0xE4)
        vertex_count = read_uint(self.fb)
        # если vertex != 0, значит есть данные - собираем
        if vertex_count != 0:            
            mesh.is_blank_mesh = False
            # получим адрес вершин и перейдем по адресу 
            vertex_adr = read_uint(self.fb)
            self.fb.seek(vertex_adr)
            # соберем вершины
            self.parse_vertex(mesh, vertex_count)
            # адрес полигонов start + 104h
            self.fb.seek(start_addr + 0x104)
            # получим адрес полигонов и их количесвто
            face_count = read_uint(self.fb)
            face_adr = read_uint(self.fb)
            self.fb.seek(face_adr)
            # соберем полигоны
            self.parse_faces(mesh, face_count)
        # добьавим меш в список. проверим список адресов. если адреса есть, то вызываем в функции саму себя для сбора слдующего адреса.
        self.mesh_list.append(mesh)
        if len(self.mesh_chunk_address_list) != 0:
            self.parse_mesh()
            
    def parse_vertex(self, mesh, vertex_count): 
        for _ in range(vertex_count):
            mesh.vertex_list.append(unpack("fff", self.fb.read(3*4)))
            # пропустим пусты данные
            self.fb.read(4)
    
    def parse_faces(self, mesh, face_count):
        for _ in range(face_count):
            mesh.face_list.append(unpack("HHH", self.fb.read(3*2)))

def build_models(mesh_list):
    # используем имя файла в качестве названия коллекции
    # создадим коллекцию
    collect_name = FILE_PATH.split("\\")[-1]
    col = bpy.data.collections.new(collect_name)
    bpy.context.scene.collection.children.link(col)
    # создадим меши
    for m in mesh_list:
        if m.is_blank_mesh:
            continue
        mesh = bpy.data.meshes.new(m.name)
        mesh.from_pydata(m.vertex_list, [], m.face_list)
        model = bpy.data.objects.new(m.name, mesh)
        # bpy.context.scene.collection.objects.link(model)
        bpy.data.collections[collect_name].objects.link(model)

def build_models_v2(mesh_list):
    for m in mesh_list:
        if m.is_blank_mesh:
            continue
        mesh = bpy.data.meshes.new(m.name)
        mesh.from_pydata(m.vertex_list, [], m.face_list)
        obj = bpy.data.objects.new(m.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        # bpy.data.collections[collect_name].objects.link(model)
        
def work():
    if len(FILE_PATH) == 0:
        raise RuntimeWarning('Укажи путь к .SCN файлу в переменную FILE_PATH.')
    parser = SCNFileParser(FILE_PATH)
    parser.parse_file()
    build_models(parser.mesh_list)
        
work()
