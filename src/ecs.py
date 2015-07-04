import weakref
import itertools


class Component(object):
    __slots__ = [
        '_entity',
        'typeid',
    ]

    @property
    def entity(self):
        return self._entity()


class Entity(object):
    __slots__ = [
        '_components',
        '__weakref__',
    ]

    def __init__(self):
        self._components = {}

    def add_component(self, component):
        if component.typeid in self._components:
            raise RuntimeError('Entity already has component of with typeid of {}'.format(component.typeid))
        component._entity = weakref.ref(self)
        self._components[component.typeid] = component

    def remove_component(self, component):
        del self._components[component.typeid]

    def get_component(self, typeid):
        return self._components[typeid]


class System(object):
    __slots__ = [
        'component_types',
    ]

    def update(self, dt, entities):
        pass


class ECSManager(object):
    def __init__(self):
        self.entities = []
        self.systems = set()

    def add_entity(self, entity):
        self.entities.append(entity)

    def remove_entity(self, entity):
        self.entities.remove(entity)

    def add_system(self, system):
        self.systems.add(system)

    def remove_system(self, system):
        self.systems.remove(system)

    def update(self, dt):
        for system in self.systems:
            components = [component for entity in self.entities for component in entity._components.values() if component.typeid in system.component_types]
            components = dict(itertools.groupby(components, lambda x: x.typeid))

            system.update(dt, components)
