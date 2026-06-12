
# @contract: M-C
def c_func(): pass

# @contract: M-B
def b_func():
    c_func()

# @contract: M-A
def a_func():
    b_func()
    c_func()
