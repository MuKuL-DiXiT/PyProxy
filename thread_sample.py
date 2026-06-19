import threading
def runable():
    for i in range(10):
        print("worker", i)
t = threading.Thread(target = runable)
t.start()

for i in range(10):
    print("main", i)
