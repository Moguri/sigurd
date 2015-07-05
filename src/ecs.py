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
        '_new_components',
        '__weakref__',
    ]

    def __init__(self):
        self._components = {}
        self._new_components = {}

    def add_component(self, component):
        if component.typeid in self._components or component.typeid in self._new_components:
            raise RuntimeError('Entity already has component with typeid of {}'.format(component.typeid))
        component._entity = weakref.ref(self)
        self._new_components[component.typeid] = component

    def remove_component(self, component):
        if component.typeid in self._components:
            del self._components[component.typeid]
        elif component.typeid in self._new_components:
            del self._new_components[component.typeid]
        else:
            raise KeyError('Enity has no component with typeid of {}'.format(component.typeid))

    def get_component(self, typeid):
        if typeid in self._components:
            return self._components[typeid]
        elif typeid in self._new_components:
            return self._new_components
        else:
            raise KeyError('Enity has no component with typeid of {}'.format(typeid))


class System(object):
    __slots__ = [
        'component_types',
    ]

    def init_components(self, dt, entities):
        pass

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

    def _get_components_by_type(self, component_types):
        components = [component for entity in self.entities for component in entity._components.values() if component.typeid in component_types]
        components = dict(itertools.groupby(components, lambda x: x.typeid))

        return components

    def update(self, dt):
        for system in self.systems:
            system.init_components(dt, self._get_components_by_type(system.component_types))

        for entity in self.entities:
            entity._components.update(entity._new_components)
            entity._new_components.clear()

        for system in self.systems:
            system.update(dt, self._get_components_by_type(system.component_types))
