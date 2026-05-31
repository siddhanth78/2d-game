import moderngl
import numpy as np
import pygame
import os

class Renderer:
    def __init__(self, screen_width, screen_height, cell_size, depth):
        self.ctx = moderngl.create_context()
        self.cell_size = cell_size
        self.depth = depth
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec2 in_world_pos;
                in float in_elevation;
                in float in_u_min;
                in float in_u_max;

                uniform vec2 screen_size;
                uniform vec2 camera;

                out vec2 v_uv;
                out float v_brightness;

                void main() {
                    vec2 iso_offset = vec2(in_elevation, -in_elevation);
                    vec2 world = in_world_pos + iso_offset + camera;
                    vec2 pos = in_vert + world;
                    vec2 ndc = (pos / screen_size) * 2.0 - 1.0;
                    gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
                    float u = in_u_min + (in_vert.x / ''' + str(float(cell_size)) + ''') * (in_u_max - in_u_min);
                    v_uv = vec2(u, 1.0 - in_vert.y / ''' + str(float(cell_size)) + ''');
                    v_brightness = pow(in_elevation / 25.0, 1.0 / 2.2);
                }
            ''',
            fragment_shader='''
                #version 330
                in vec2 v_uv;
                in float v_brightness;
                out vec4 f_color;
                uniform sampler2D atlas;
                void main() {
                    vec4 tex_color = texture(atlas, v_uv);
                    f_color = vec4(tex_color.rgb * v_brightness, tex_color.a);
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
                (self.vbo_instance, '2f 1f 1f 1f /i', 'in_world_pos', 'in_elevation', 'in_u_min', 'in_u_max'),
            ]
        )

    def build_atlas(self, cell_data, cell_size):
        n = len(cell_data)
        atlas_surf = pygame.Surface((cell_size * n, cell_size), pygame.SRCALPHA)
        self.tile_uvs = {}
        for i, (name, (color, path)) in enumerate(cell_data.items()):
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (cell_size, cell_size))
                atlas_surf.blit(img, (i * cell_size, 0))
            else:
                pygame.draw.rect(atlas_surf, (*color, 255), (i * cell_size, 0, cell_size, cell_size))
            self.tile_uvs[name] = (i / n, (i + 1) / n)
        img_data = pygame.image.tobytes(atlas_surf, 'RGBA', True)
        self.atlas = self.ctx.texture((cell_size * n, cell_size), 4, img_data)
        self.atlas.filter = moderngl.NEAREST, moderngl.NEAREST
        self.atlas.use(0)
        self.prog['atlas'].value = 0

    def init_selection(self):
        self.sel_prog = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                uniform vec2 screen_size;
                uniform vec2 position;
                out vec2 v_uv;
                void main() {
                    v_uv = in_vert;
                    vec2 pos = in_vert + position;
                    vec2 ndc = (pos / screen_size) * 2.0 - 1.0;
                    gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330
                in vec2 v_uv;
                out vec4 f_color;
                uniform float cell_size;
                uniform float thickness;
                void main() {
                    float t = thickness;
                    float cs = cell_size;
                    if (v_uv.x < t || v_uv.x > cs - t || v_uv.y < t || v_uv.y > cs - t)
                        f_color = vec4(1.0, 1.0, 1.0, 1.0);
                    else
                        discard;
                }
            '''
        )
        cs = float(self.cell_size)
        quad = np.array([
            0, 0, cs, 0, 0, cs,
            cs, 0, cs, cs, 0, cs,
        ], dtype='f4')
        self.sel_vbo = self.ctx.buffer(quad.tobytes())
        self.sel_vao = self.ctx.vertex_array(self.sel_prog, [(self.sel_vbo, '2f', 'in_vert')])
        self.sel_prog['screen_size'].value = (float(self.screen_width), float(self.screen_height))
        self.sel_prog['cell_size'].value = float(self.cell_size)
        self.sel_prog['thickness'].value = 3.0

    def render_selection(self, world_x, world_y, camera_x, camera_y):
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.sel_prog['position'].value = (float(world_x + camera_x), float(world_y + camera_y))
        self.sel_vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.BLEND)

    def upload(self, instance_data):
        self.instance_count = len(instance_data)
        if self.instance_count > 0:
            self.vbo_instance.write(instance_data.tobytes())

    def render(self, camera_x, camera_y):
        self.ctx.clear(0.0, 0.0, 0.0)
        self.prog['camera'].value = (float(camera_x), float(camera_y))
        if self.instance_count > 0:
            self.atlas.use(0)
            self.vao.render(moderngl.TRIANGLES, instances=self.instance_count)