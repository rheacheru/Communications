import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def is_jpg_or_jpeg(filename):
    return filename.lower().endswith(('.jpg', '.jpeg'))

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            print(f"Directory created: {event.src_path}")
        else:
            print(f"File created: {event.src_path}")

if __name__ == "__main__":
    handler = MyHandler()
    observer = Observer()
    observer.schedule(handler, path='/path/to/watched/folder', recursive=True)

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
