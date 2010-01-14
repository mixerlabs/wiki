import sys

from . import linkgraph

linkgraph.initialize()

# Bug #622. Remove this when widgets are playing.
#
# The creoleparser can be kind of retarded about parsing inline
# elements. For larger pages, it is happy to consume *a lot* of stack.
if sys.getrecursionlimit() < 3000:
    sys.setrecursionlimit(3000)
