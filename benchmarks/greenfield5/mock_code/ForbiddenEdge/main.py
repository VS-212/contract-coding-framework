
# @contract: M-B
def b_func():
    a_func() # Forbidden edge!

# @contract: M-A
def a_func():
    b_func()
