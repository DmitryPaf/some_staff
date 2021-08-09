def create_gcd(len):
    '''
    a(1) = 7, a(n) = a(n-1) + gcd(n, a(n-1)) 
    '''
    tmp = []
    tmp.append(7)
    for i in range(1, len):
        tmp.append(tmp[i - 1] + math.gcd(i+1, tmp[i - 1]))
    return tmp


def create_diff_suc(n):
    '''
    differences between successive elements of the sequence 
    '''
    
    lst = create_gcd(n)
    tmp = []
    for i in range(1,len(lst)):
        tmp.append(lst[i] - lst[i-1])
    tmp.insert(0, 1)
    return tmp


def remove_ones(n):
    '''
    Removing the 1s gives 
    '''
    lst = create_diff_suc(n*2000)
    tmp =  [i for i in lst if i != 1]
    return tmp[:n]
