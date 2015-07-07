import panda3d.core as p3d
import panda3d.bullet as bullet

import ecs


class HitBoxComponent(ecs.Component):
    __slots__ = [
        'physics_node',
    ]
    typeid = 'PHY_HITBOX'

    def __init__(self):
        xform_state = p3d.TransformState.make_pos(p3d.LVector3f(0, 0, 0.9))
        shape = bullet.BulletBoxShape(p3d.LVector3f(0.25, 0.25, 0.8))
        self.physics_node = bullet.BulletGhostNode('HitBox')
        self.physics_node.add_shape(shape, xform_state)


class PhysicsSystem(ecs.System):
    __slots__ = [
        'physics_world',
    ]

    def __init__(self):
        self.component_types = ['PHY_HITBOX']
        self.physics_world = bullet.BulletWorld()

        phydebug = bullet.BulletDebugNode('Physics Debug')
        phydebug.show_wireframe(True)
        phydebug.show_bounding_boxes(True)
        phydebugnp = base.render.attach_new_node(phydebug)
        # Uncomment to show debug physics
        # phydebugnp.show()
        self.physics_world.set_debug_node(phydebug)

        def update_physics(task):
            dt = globalClock.getDt()
            self.physics_world.do_physics(dt)
            return task.cont
        base.taskMgr.add(update_physics, 'Physics')

    def init_components(self, dt, components):
        for hit_box in components.get('PHY_HITBOX', []):
            np_component = hit_box.entity.get_component('NODEPATH')
            np_component.nodepath.attach_new_node(hit_box.physics_node)
            self.physics_world.attach_ghost(hit_box.physics_node)