# Rc Cars 3D Models Exporter
**Rc Cars 3D Models Exporter** - это скрипт, написанный на языке Python. Скрипт предназначен для экспорта 3D моделей из файлов компьютерной игры ***"Rc Cars"*** в программу **Blender**. В странах СНГ игра более известна под названием ***"Недетские гонки"***.

# Как запустить скрипт?
### Для запуска скрипта нам понадобиться 3 вещи:
1. Файл игры формата `.sb`. В файлах этого формата хранится информация о всех объектах игры.
2. 3D редактор **Blender 2.80** версии и _выше_.
3. Скрипт **rccars_3d_models_exporter.py**.

### Чтобы запустить скрипт надо:
1. Запустить программу **Blender**. После запуска желательно удалить лишние объекты(куб, свет, камера), чтобы не мешали.
2. Открыть окно **Scripting**.
3. Найти скрипт **rccars_3d_models_exporter.py** в той папке, в которую вы его сохранили, и открыть.
4. В тексте скрипта найти переменную **FILE_PATH** и прописать в ней путь к `.sb` файлу. Пример написания пути к файлу в Windows и Linux(мб кто-то бдует запускать в Linux. LOL):
```
# Windows
FILE_PATH = "C:\\my\\path\\to\\file.sb"
# Linux
FILE_PATH = "/my/path/to/file.sb"
```
5. Запустить скрипт и подождать. Готово!

