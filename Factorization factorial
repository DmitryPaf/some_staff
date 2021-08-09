def decomp(n):
    pr = erato(n)
    sums = []
    x = []
    for i in pr:
        steepen = 1
        summa = 0
        while i ** steepen <= n:
            summa = summa + (n // i ** steepen)
            steepen = steepen + 1
        sums.append(summa)
    for i in range(len(pr)):
        if sums[i] > 1:
            x.append(str(pr[i]) + "^" + str(sums[i]))
        else:
            x.append(str(pr[i]))
    return ' * '.join(str(i) for i in x)


def erato(n):
    a = list(range(n + 1))
    a[1] = 0
    lst = []

    i = 2
    while i <= n:
        if a[i] != 0:
            lst.append(a[i])
            for j in range(i, n + 1, i):
                a[j] = 0
        i += 1
    return lst
