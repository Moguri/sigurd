from direct.showbase.DirectObject import DirectObject
import panda3d.core as p3d


class PlayerController(DirectObject):
    SPEED = p3d.LVector3f(0.1, 0.2, 0.0)

    def __init__(self, camera):
        self.camera = camera
        self.node_path = base.render.attach_new_node('player')
        self.camera.reparent_to(self.node_path)
        self.camera.set_pos(0, 0, 1.7)

        self.movement = p3d.LVector3f(0, 0, 0)

        self.accept('w', self.update_movement, ['forward', True])
        self.accept('w-up', self.update_movement, ['forward', False])
        self.accept('s', self.update_movement, ['backward', True])
        self.accept('s-up', self.update_movement, ['backward', False])
        self.accept('a', self.update_movement, ['left', True])
        self.accept('a-up', self.update_movement, ['left', False])
        self.accept('d', self.update_movement, ['right', True])
        self.accept('d-up', self.update_movement, ['right', False])

        base.taskMgr.add(self.update, 'PlayerTask')

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

    def update(self, task):
        new_pos = p3d.LVector3f(self.movement)
        new_pos.normalize()
        new_pos.componentwiseMult(self.SPEED)
        new_pos += self.node_path.get_pos()

        self.node_path.set_pos(new_pos)

        return task.cont
