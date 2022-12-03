"""
TODO
"""

from cobbler.items.item import Item


class Template(Item):
    """
    TODO
    """

    TYPE_NAME = "template"
    COLLECTION_TYPE = "template"

    def make_clone(self):
        pass
