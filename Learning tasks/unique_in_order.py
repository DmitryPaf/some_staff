def unique_in_order(iterable):
    list = []
    if iterable:
        list.append(iterable[0])
    for letter in iterable:
        if letter != list[-1]:
            list.append(letter)
    return list
