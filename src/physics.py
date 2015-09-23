import panda3d.core as p3d
import panda3d.bullet as bullet

import ecs


class HitResult(object):
    def __init__(self, bullet_hit):
        self.position = bullet_hit.get_hit_pos()
        self.normal = bullet_hit.get_hit_normal()
        self.node = bullet_hit.get_node()
        self.t = bullet_hit.get_hit_fraction()
        self.triangle_index = bullet_hit.get_triangle_index()
        self.component = self.node.get_python_tag('component')

    def __repr__(self):
        return '<HitResult position:{} normal:{} node:{} t:{} triangle_index:{}'.format(
            self.position,
            self.normal,
            self.node,
            self.t,
            self.triangle_index
        )


class HitBoxComponent(ecs.Component):
    __slots__ = [
        'physics_node',
    ]
    typeid = 'PHY_HITBOX'

    def __init__(self):
        super().__init__()
        xform_state = p3d.TransformState.make_pos(p3d.LVector3f(0, 0, 0.9))
        shape = bullet.BulletBoxShape(p3d.LVector3f(0.25, 0.25, 0.8))
        self.physics_node = bullet.BulletGhostNode('HitBox')
        self.physics_node.add_shape(shape, xform_state)
        self.physics_node.set_python_tag('component', self)

    def cleanup(self):
        self.physics_node.clear_python_tag('component')
        psys = base.ecsmanager.get_system('PhysicsSystem')
        psys.physics_world.remove(self.physics_node)


class StaticPhysicsMeshComponent(ecs.Component):
    __slots__ = [
        'physics_node',
    ]
    typeid = 'PHY_STATICMESH'

    def __init__(self, geom, offset=p3d.LVector3f(0, 0, 0)):
        super().__init__()

        mesh = bullet.BulletTriangleMesh()
        for i in range(geom.node().get_num_geoms()):
            mesh.add_geom(geom.node().get_geom(i))
        shape = bullet.BulletTriangleMeshShape(mesh, dynamic=False)

        self.physics_node = bullet.BulletRigidBodyNode('StaticMesh')
        xform_state = p3d.TransformState.make_pos(offset)
        self.physics_node.add_shape(shape, xform_state)
        self.physics_node.set_python_tag('component', self)

    def cleanup(self):
        self.physics_node.clear_python_tag('component')
        psys = base.ecsmanager.get_system('PhysicsSystem')
        psys.physics_world.remove(self.physics_node)


class PhysicsSystem(ecs.System):
    __slots__ = [
        'physics_world',
    ]

    component_types = [
        'PHY_HITBOX',
        'PHY_STATICMESH',
    ]

    def __init__(self):
        self.physics_world = bullet.BulletWorld()

        phydebug = bullet.BulletDebugNode('Physics Debug')
        phydebug.show_wireframe(True)
        phydebug.show_bounding_boxes(True)
        phydebugnp = base.render.attach_new_node(phydebug)
        # Uncomment to show debug physics
        phydebugnp.show()
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
            self.physics_world.attach(hit_box.physics_node)

        for static_mesh in components.get('PHY_STATICMESH', []):
            np_component = static_mesh.entity.get_component('NODEPATH')
            np_component.nodepath.attach_new_node(static_mesh.physics_node)
            self.physics_world.attach(static_mesh.physics_node)

    def ray_cast(self, from_pos, to_pos, all_hits=False, mask=None):
        hits = []

        # Draw debug lines
        # lineseg = p3d.LineSegs('debug ray')
        # lineseg.reset()
        # lineseg.move_to(from_pos)
        # lineseg.draw_to(to_pos)
        # debug_line = lineseg.create(False)
        # base.render.attach_new_node(debug_line)

        if all_hits:
            if mask:
                bhits = self.physics_world.ray_test_all(from_pos, to_pos, mask)
            else:
                bhits = self.physics_world.ray_test_all(from_pos, to_pos)
            for bhit in bhits.get_hits():
                hits.append(HitResult(bhit))
        else:
            if mask:
                bhit = self.physics_world.ray_test_closest(from_pos, to_pos, mask)
            else:
                bhit = self.physics_world.ray_test_closest(from_pos, to_pos)
            if bhit.has_hit():
                hits.append(HitResult(bhit))

        return hits
