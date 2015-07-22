import ecs

class EffectComponent(ecs.Component):
    __slots__ = [
        'cmd_queue',
        'effect_type'
    ]
    typeid = 'EFFECT'

    def __init__(self):
        super().__init__()
        self.cmd_queue = set()

class PrintEffectComponent(EffectComponent):
    __slots__ = ['message']
    effect_type = 'PRINT'

    def __init__(self, effect_data):
        super().__init__()
        EffectComponent.__init__(self)
        self.message = effect_data['message']

class EffectSystem(ecs.System):
    __slots__ = []

    component_types = [
        'EFFECT',
    ]

    def update(self, dt, components):
        for component in components['EFFECT']:
            cfunc = component.effect_type.lower() + '_effect'
            if 'ACTIVATE' in component.cmd_queue:
                getattr(self, cfunc)(dt, component)
                component.cmd_queue.remove('ACTIVATE')

    def print_effect(self, dt, component):
        print(component.message)


