# RCCars 3D Models Exporter v 1.1
# ** - обозначает отображение чанков в .sb файле. Т.к. данные в .sb файле записаны "зеркально", то, 
# если в .sb файле чанк записан как **0092h, то в оригинале это значение 9200h. Как и **HSEM - это MESH.
# Помечаю для более удобного чтения чанков в файле при его разборе. 
# P.S. ****h - h обозначает, что число записано в 16-й системе счисления. Как и префикс 0x в иных случаях обозначает тоже самое.
import os
import bpy
from struct import *

# Cигнатура .sb файла - 3801h(**0138h). Всего 2 сигнатуры. 2ю не помню. Потом как-нибудь впишу. 
# Обозначает цифровую подпись файла. Как к примеру, все .png файлы начинаются с сигнатуры 0x89504E470D0A1A0A,
# что означает .png формат.
FILE_PATH = ""
SB_FILE_SIGNATURE = 0x3801

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


class MODLMod(object):
    def __init__(self):
        self.name = None
        self.mesh_list = []


class MESHMod(object):
    def __init__(self):
        self.name = None
        self.is_blank_mesh = True
        self.start = None
        self.end = None
        self.vertex_list = []
        self.face_list = []


class SBFileParser(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_size = None
        self.file_cursor = None
        self.mods_hex_list = []
        self.mods_str_list = []
        self.models_list = []

    def parse_file(self):
        self.init_file()        
        try:
            signa = read_ushort(self.fb)
            # проверяем правильногсть сигнатуры и является ли файл .sb файлом 
            if signa != SB_FILE_SIGNATURE and self.file_path[-3:] == ".sb":
                # raise RuntimeError("Invalid file signature: %08d" % (magic))
                raise RuntimeError("Неверная сигнатура файла: %08d. Либо выбран не тот файл." % (signa))
            self.parse_file_headers()
            self.parse_mods()
        except Exception as ex:
            print(self.file_cursor)
            raise ex
        finally:
            self.fb.close()

    def parse_mods(self):
        while True:
            # Т.к. неизвестно какой чанк сколько занимет памяти, то придется искать по байтам.
            # Сперва парсим mod_entry_chunk 9200h(**0092h). Этот чанк начало любого модуля.
            # В некоторых известных случаях можно парсить по указателям.
            fst_byte = read_char(self.fb)
            if fst_byte == 0:
                sec_byte = read_char(self.fb)
                if sec_byte == 0x92:
                    self.fb.read(4) # пропускаем возможный указатель на конец модуля
                    MOD = read_uint(self.fb)
                    # проверяем является ли чанк модулем
                    if MOD in self.mods_hex_list:
                        # если чанк MODL - начинаем парсить
                        if MOD == 0x4D4F444C: #MODL
                            # берем контрольный курсор, пропускаем entry чанк(+2). 
                            # в функции возьмем указатель на конец модуля
                            self.file_cursor += 2
                            self.fb.seek(self.file_cursor)
                            self.parse_MODL()
                        else:
                            self.file_cursor += 10
                    else:
                        self.file_cursor += 1
                        self.fb.seek(self.file_cursor)
                else:
                    self.file_cursor += 1
                    self.fb.seek(self.file_cursor)
            else:
                self.file_cursor += 1
                
            if self.file_cursor >= self.file_size:
                break

    def parse_MODL(self):
        modl = MODLMod()
        # читаем указатель на конец модуля
        mod_end = read_uint(self.fb)
        self.file_cursor += 4
        # пропускаем название MODa
        self.file_cursor += 4
        # пропускаем чанк 4003h(**0340h) и указатель на конец данных
        self.file_cursor += 6
        self.fb.seek(self.file_cursor)
        # читаем название модели
        modl.name = read_string(self.fb)
        # ищем меши
        mesh_list = []
        while True:
            # Снова парсим mod_entry_chunk 9200h(**0092h), чтобы найти меш. 
            fst_byte = read_char(self.fb)
            if fst_byte == 0:
                sec_byte = read_char(self.fb)
                if sec_byte == 0x92:
                    self.fb.read(4) # пропускаем возможный указатель на конец модуля
                    MOD = read_uint(self.fb)
                    # проверяем является ли чанк модулем
                    if MOD in self.mods_hex_list:
                        # если чанк MESH - начинаем парсить
                        if MOD == 0x4D455348: #MESH
                            # т.к. все совпало по байтам и значения найдены, надо вернуться на enytry_chunk
                            # и пропустить его. А потом в функции parse_MESH получить указатель на конец модуля
                            # self.file_cursor += 2
                            # self.fb.seek(self.file_cursor)
                            # пока писал скрипт, выяснил, что у MESH внутри одного MODL одинаковый указатель на конец модуля 
                            # с пересечением других MESH модулей. В общем, ридется искать меши иначе.
                            # Будем рассчитывать начало и конец меша, потом парсить его.
                            new_mesh = self.init_mesh()
                            mesh_list.append(new_mesh)
                        else:
                            self.file_cursor += 10
                    else:
                        self.file_cursor += 1
                        self.fb.seek(self.file_cursor)
                else:
                    self.file_cursor += 1
                    self.fb.seek(self.file_cursor)
            else:
                self.file_cursor += 1

            if self.file_cursor >= mod_end:
                break
        
        # запмоним где осатновились
        last_stop = self.file_cursor

        # соберем информацию о мешах
        for mesh in mesh_list:
            # парсим меш
            self.parse_MESH(mesh)
            # добавляем мешь в модель
            modl.mesh_list.append(mesh)
        # добавляем модель в список моделей
        self.models_list.append(modl)
        # после парсинга модели и мешей возвращаемся на точку где остановились и идем дальше
        self.fb.seek(last_stop)

    def parse_MESH(self, mesh):
        # уже, имея начало и конец меша, пройдемся по байтам меша
        # сперва зададим стартовую позицию курcора в файле 
        # можно сразу пропустить 16 начальных байтов + длину строки имени меша + 0й байт строки == 17 + len(name)
        self.fb.seek(mesh.start + 17 +len(mesh.name))
        cursor = self.fb.tell()
        while True:
            # В отлии от поиска чанков модели, чанки с данными искать будет чуточку сложнее. 
            # Дабы не спутать чанк с данными:
            # 1. зная чанк, 2. его структуру данных, 3. имея указатель на конец данных,
            # будем создавать контрольную сумму и сверять с длиной байт от начала, до конца.

            # Ищем чанк 7411h(**1174h), который хранит координаты вершин(vertex). Тип данных у координат 3 float
            # Всего 1 чанк с вертексами на 1 MESH.
            # Формула контрольной суммы будет таковой:
            # Чанк **1174h[2 байта] + указатель на конец данных[4 байта] + число вершин[4 байта] * координаты вершин[3*4 байта]
            fst_byte = read_char(self.fb)
            if fst_byte == 0x11:
                sec_byte = read_char(self.fb)
                if sec_byte == 0x74:
                    # считаем сумму и сверяем с указателем на конец
                    # указатель
                    end_data = read_uint(self.fb)
                    # кол-во вершин
                    vertex_count = read_uint(self.fb)
                    control_sum = 2 + 4 + 4 + vertex_count * 3 * 4
                    if end_data - cursor == control_sum:
                        # успех. сумма совпала. некоторые меши в .sb файле не имеют модели.. они просто пусты.
                        # поэтому решил добавить булевое значение is_blank_mesh, которое это отображает
                        mesh.is_blank_mesh = False
                        mesh.vertex_list = [unpack("fff", self.fb.read(3*4)) for _ in range(vertex_count)]
                        # переместим контрольный указатель
                        cursor += control_sum
                    else:
                        cursor += 1
                        self.fb.seek(cursor)
                else:
                    cursor += 1
                    self.fb.seek(cursor)

            # Ищем чанк 3419h(**1934h), который хранит инфу об 1 полигоне(face). Полигон состоит из x вершин.(но скорее всего только из 3). Тип данных int.
            # Таких чанков может быть много. Сколько полигонов, столько чанков.
            # Формула контрольной суммы будет таковой:
            # Чанк 1934h[2 байта] + указатель на конец данных[4 байта] + x-число точек в полигоне[4 байта] * id вершин полигонов[x*4 байта]
            # обычно полигон состоит из 3 точек, но кто знает. мб и из большего кол-ва, поэтому берем за x
            elif fst_byte == 0x19:
                sec_byte = read_char(self.fb)
                if sec_byte == 0x34:
                    # считаем сумму и сверяем с указателем на конец
                    # указатель
                    end_data = read_uint(self.fb)
                    # кол-во вершин у полигона
                    face_matrix_count = read_uint(self.fb)
                    control_sum = 2 + 4 + 4 + face_matrix_count * 4
                    if end_data - cursor == control_sum:
                        # успех. сумма совпала. добавим полигон в список
                        mesh.face_list.append(unpack("I" * face_matrix_count, self.fb.read(4 * face_matrix_count)))
                        cursor += control_sum
                    else:
                        cursor += 1
                        self.fb.seek(cursor)
                else:
                    cursor += 1
                    self.fb.seek(cursor)
            else:
                cursor += 1
            
            if cursor >= mesh.end:
                return

    def parse_file_headers(self):
        try:
            # По идее заголовки закономерны, но стоит проверить на целосттность. Малоли длина байт разная.
            # Поэтому можно пошагово прописать функцию. 
            # читаем адрес следующего чанка и преходим к нему
            new_cursor = read_uint(self.fb)
            self.fb.seek(new_cursor)
            # следующим чанком должен быть 4802h(**0248h). Текстовый заголовок. Проверям.
            chunk = read_ushort(self.fb)
            if chunk != 0x4802:
                raise Exception({"invalid_chunk": "0x4802"})
            # чанк совпал. пропустим его. он не важен. берем указатель на следующий чанк и переходим.
            new_cursor = read_uint(self.fb)
            self.fb.seek(new_cursor)
            # вот тут уже надо собрать все MOD, чтобы знать какие моды используются в файле и проводить с ними проверку,
            # дабы не прочесть что-то не так по ошибке при парсинге.
            # MOD - непонятно что подразумевается под MOD, поэтом называю модуль.
            # Пример MOD: MOD_MESH, MOD_CAMERA и т.д.
            # 9A00h(**009Ah) чанк инициализации модуля .
            chunk = read_ushort(self.fb)
            if chunk != 0x9A00:
                raise Exception({"invalid_chunk": "0x9A00"})
            # собирем MODs
            while True:
                new_cursor = read_uint(self.fb)
                modb = self.fb.read(4)
                self.mods_hex_list.append(unpack("I", modb)[0])
                # для просмотра при дебаге. можно убрать этот список
                self.mods_str_list.append(modb[::-1].decode('cp437'))
                # проверим следующий чанк.
                # если не равен 9A00h, значит все MOD собраны
                self.fb.seek(new_cursor)
                chunk = read_ushort(self.fb)
                if chunk != 0x9A00:
                    break
            # откатим курсор файла назад на 2 байта и зададим нашему контрольному курсору последнюю позицию
            cur = self.fb.tell() - 2
            self.fb.seek(cur)
            self.file_cursor = cur
        except Exception as e:
            raise e

    def init_file(self):
        self.fb = open(self.file_path, "rb")
        self.file_size = self.fb.seek(0, os.SEEK_END)
        self.file_cursor = 1
        self.fb.seek(0)

    def init_mesh(self):
        mesh = MESHMod()
        # добавим старт меша
        mesh.start = self.file_cursor
        # пропускаем mod чанк
        self.file_cursor += 2
        # пропускаем указатель
        self.file_cursor += 4
        # пропускаем название MODa
        self.file_cursor += 4
        # пропускаем чанк 4003h(**0340h) и указатель
        self.file_cursor += 6
        self.fb.seek(self.file_cursor)
        # читаем имя меша
        mesh.name = read_string(self.fb)
        # будем самостоятельно искать конец модуля, уперевшись 
        # в следующий модуль
        while True:
            fst_byte = read_char(self.fb)
            if fst_byte == 0:
                sec_byte = read_char(self.fb)
                if sec_byte == 0x92:
                    self.fb.read(4) # пропускаем возможный указатель на конец модуля
                    MOD = read_uint(self.fb)
                    # проверяем является ли чанк модулем
                    if MOD in self.mods_hex_list:
                        # нашли новый модуль, значит это конец меша. записываем адрес
                        mesh.end = self.file_cursor
                        # переводим указатель файла на начало нового модуля
                        self.fb.seek(self.file_cursor)
                        # вернем меш
                        return mesh
                else:
                    self.file_cursor += 1
                    self.fb.seek(self.file_cursor)
            else:
                self.file_cursor += 1

def build_models(modl):
    # создадим коллекцию
    col = bpy.data.collections.new(modl.name)
    bpy.context.scene.collection.children.link(col)
    # создадим меши
    for m in modl.mesh_list:
        if m.is_blank_mesh:
            continue
        mesh = bpy.data.meshes.new(m.name)
        mesh.from_pydata(m.vertex_list, [], m.face_list)
        model = bpy.data.objects.new(m.name, mesh)
        # bpy.context.scene.collection.objects.link(model)
        bpy.data.collections[modl.name].objects.link(model)

def work(file_path):
    if len(file_path) == 0:
        raise RuntimeWarning('Укажи путь к .sb файлу в переменную FILE_PATH.')
    sb_parser = SBFileParser(file_path)
    sb_parser.parse_file()
    for modl in sb_parser.models_list:
        build_models(modl)

work(FILE_PATH)
