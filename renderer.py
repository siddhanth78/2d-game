import moderngl
import numpy as np

class Renderer:
    def __init__(self, screen_width, screen_height, cell_size, depth):
        self.ctx = moderngl.create_context()
        self.cell_size = cell_size
        self.depth = depth

        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec2 in_world_pos;
                in float in_elevation;
                in vec3 in_color;

                uniform vec2 screen_size;
                uniform vec2 camera;

                out vec3 v_color;

                void main() {
                    vec2 iso_offset = vec2(in_elevation, -in_elevation);
                    vec2 world = in_world_pos + iso_offset + camera;
                    vec2 pos = in_vert + world;
                    vec2 ndc = (pos / screen_size) * 2.0 - 1.0;
                    gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
                    float brightness = pow(in_elevation / 25.0, 1.0 / 2.2);
                    v_color = in_color * brightness;
                }
            ''',
            fragment_shader='''
                #version 330
                in vec3 v_color;
                out vec4 f_color;
                void main() {
                    f_color = vec4(v_color, 1.0);
                }
            '''
        )

        cs = float(cell_size)
        quad = np.array([
            0, 0,
            cs, 0,
            0, cs,
            cs, 0,
            cs, cs,
            0, cs,
        ], dtype='f4')

        self.prog['screen_size'].value = (float(screen_width), float(screen_height))
        self.vbo_quad = self.ctx.buffer(quad.tobytes())
        self.vbo_instance = self.ctx.buffer(reserve=4*1024*1024)
        self.instance_count = 0

        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo_quad, '2f', 'in_vert'),
                (self.vbo_instance, '2f 1f 3f /i', 'in_world_pos', 'in_elevation', 'in_color'),
            ]
        )

    def upload(self, instance_data):
        self.instance_count = len(instance_data)
        if self.instance_count > 0:
            self.vbo_instance.write(instance_data.tobytes())

    def render(self, camera_x, camera_y):
        self.ctx.clear(0.0, 0.0, 0.0)
        self.prog['camera'].value = (float(camera_x), float(camera_y))
        if self.instance_count > 0:
            self.vao.render(moderngl.TRIANGLES, instances=self.instance_count)