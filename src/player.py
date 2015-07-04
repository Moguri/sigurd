from direct.showbase.DirectObject import DirectObject
import panda3d.core as p3d

import ecs


class CharacterComponent(ecs.Component):
    __slots__ = [
        "speed",
        "movement",
    ]

    typeid = "CHARACTER"

    def __init__(self):
        self.speed = p3d.LVector3f(0.04, 0.04, 0.0)
        self.movement = p3d.LVector3f(0, 0, 0)


def clamp(value, lower, upper):
    return max(min(value, upper), lower)


class PlayerSystem(ecs.System, DirectObject):
    component_types = [
        "CHARACTER",
    ]

    def __init__(self):
        self.movement = p3d.LVector3f(0, 0, 0)
        self.camera_pitch = 0
        self.camera_heading = 0
        self.mousex_sensitivity = 25
        self.mousey_sensitivity = 25

        self.accept('w', self.update_movement, ['forward', True])
        self.accept('w-up', self.update_movement, ['forward', False])
        self.accept('s', self.update_movement, ['backward', True])
        self.accept('s-up', self.update_movement, ['backward', False])
        self.accept('a', self.update_movement, ['left', True])
        self.accept('a-up', self.update_movement, ['left', False])
        self.accept('d', self.update_movement, ['right', True])
        self.accept('d-up', self.update_movement, ['right', False])

    def update_movement(self, direction, activate):
        move_delta = p3d.LVector3(0, 0, 0)

        if direction == 'forward':
            move_delta.set_y(1)
        elif direction == 'backward':
            move_delta.set_y(-1)
        elif direction == 'left':
            move_delta.set_x(-1)
        elif direction == 'right':
            move_delta.set_x(1)

        if not activate:
            move_delta *= -1

        self.movement += move_delta

    def update(self, dt, components):
        for char in components['CHARACTER']:
            nodepath = char.entity.get_component('NODEPATH').nodepath

            # Position
            new_pos = nodepath.getMat(base.render).xformVec(self.movement)
            new_pos.normalize()
            new_pos.componentwiseMult(char.speed)
            new_pos += nodepath.get_pos()
            nodepath.set_pos(new_pos)

            # Rotation
            if base.mouseWatcherNode.has_mouse():
                mouse = base.mouseWatcherNode.get_mouse()
                halfx = base.win.get_x_size() / 2
                halfy = base.win.get_y_size() / 2
                base.win.move_pointer(0, halfx, halfy)

                self.camera_pitch += mouse.y * self.mousey_sensitivity
                self.camera_pitch = clamp(self.camera_pitch, -75, 75)

                self.camera_heading += -mouse.x * self.mousex_sensitivity

            nodepath.set_h(self.camera_heading)
            base.camera.set_p(self.camera_pitch)


