from zope.interface import Interface, Attribute


class IApplication(Interface):

    name = Attribute("C{str} Application name")
    version = Attribute("C{str} Application version")
    loadlist = Attribute("C{list} of modules to load with the application")
    module_prefixes = Attribute("C{list} of modules to get unloaded with the"
                                " application.")
    module = Attribute("C{str} canonical name of the module the application "
                       "comes from")

    def load():
        '''Loads application'''

    def unload():
        '''Unloads application'''
