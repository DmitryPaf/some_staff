def nico(key, message):
    message = [i for i in message]
    x = sort_by_ord(key)
    tmp = []
    while len(message) % len(x):
        message.append(" ")
    while message:
        for i in x:
            tmp.append(message[i])
        message = message[len(x):]
    return "".join(tmp)


def sort_by_ord(key):

    x = [ord(c) - 96 for c in key]
    tmp = []
    for i in sorted(x):
        tmp.append(x.index(i))
    return tmp
