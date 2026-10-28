"""ModernGL renderer: generative visuals driven by the bow, corner-pinned.

Three passes per frame, all fullscreen quads:

  1. fade   -- darken the accumulation buffer a little (this makes the trails)
  2. stroke -- additively draw the glowing bow segment into the accumulation
  3. warp   -- sample the accumulation through the inverse homography so the
               content lands on the calibrated quad on the physical surface

Keeping the trail in an accumulation buffer means motion history costs one
texture rather than a growing list of points on the CPU.
"""

import moderngl
import numpy as np

# A single quad covering clip space, reused by every pass.
_QUAD = np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4")

_VERT = """
#version 330 core
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;          // clip space -> [0,1]
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

_FADE_FRAG = """
#version 330 core
out vec4 f_color;
uniform float u_fade;
void main() { f_color = vec4(0.0, 0.0, 0.0, u_fade); }
"""

_STROKE_FRAG = """
#version 330 core
in vec2 v_uv;
out vec4 f_color;

uniform vec2  u_a;        // bow endpoint A, content uv
uniform vec2  u_b;        // bow endpoint B, content uv
uniform float u_speed;    // normalized 0..1-ish
uniform float u_angle;    // radians
uniform float u_time;
uniform float u_aspect;   // width / height, keeps the glow circular
uniform float u_ok;       // 1 while tracking, 0 when lost

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

float segDist(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return length(pa - ba * h);
}

void main() {
    if (u_ok < 0.5) { f_color = vec4(0.0); return; }

    // Work in an aspect-corrected space so circles stay circular.
    vec2 p = vec2(v_uv.x * u_aspect, v_uv.y);
    vec2 a = vec2(u_a.x * u_aspect, u_a.y);
    vec2 b = vec2(u_b.x * u_aspect, u_b.y);

    float d = segDist(p, a, b);

    // Hue drifts with bow angle, brightness rides on speed.
    float hue  = fract(0.55 + u_angle / 6.2831 * 0.35 + u_time * 0.01);
    float sat  = 0.55 - 0.35 * clamp(u_speed, 0.0, 1.0);
    float boost = 0.35 + 1.65 * clamp(u_speed, 0.0, 1.0);

    float core = exp(-d * 420.0) * 1.20;         // tight bright filament
    float halo = exp(-d *  55.0) * 0.30 * boost; // soft bloom around it
    float glow = core + halo;

    f_color = vec4(hsv2rgb(vec3(hue, sat, 1.0)) * glow, 1.0);
}
"""

_WARP_FRAG = """
#version 330 core
in vec2 v_uv;
out vec4 f_color;

uniform sampler2D u_tex;
uniform mat3  u_Hinv;      // projector uv -> content uv
uniform float u_grid;      // >0 draws the calibration grid
uniform float u_handles;   // >0 draws the draggable corner handles
uniform vec2  u_corners[4];// corner positions, projector uv (y-down)
uniform int   u_sel;       // which corner is selected
uniform float u_paspect;   // projector aspect, keeps handles round

void main() {
    // v_uv is y-up; the warp is defined in y-down projector space so that
    // corner 1 is the visually top-left one.
    vec2 puv = vec2(v_uv.x, 1.0 - v_uv.y);
    vec3 c = u_Hinv * vec3(puv, 1.0);
    if (abs(c.z) < 1e-6) { f_color = vec4(0.0); discard; }
    vec2 uv = c.xy / c.z;

    // Outside the mapped quad there is no content: keep the projector black.
    // We do not return early, so the handles can still draw over it.
    bool inside = !(uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0);
    vec3 col = inside ? texture(u_tex, uv).rgb : vec3(0.0);

    if (inside && u_grid > 0.5) {
        // 8x8 grid plus a border, drawn in content space so it warps with the
        // quad. Widths are measured in screen-space derivatives (fwidth) so
        // the lines stay a constant pixel width however the quad is squashed
        // — a grid that thins to nothing is useless for aligning a surface.
        vec2 gv = uv * 8.0;
        vec2 gd = abs(fract(gv - 0.5) - 0.5) / max(fwidth(gv), vec2(1e-5));
        float line = 1.0 - smoothstep(0.0, 1.5, min(gd.x, gd.y));

        vec2 ed = min(uv, 1.0 - uv) / max(fwidth(uv), vec2(1e-5));
        float border = 1.0 - smoothstep(0.0, 2.5, min(ed.x, ed.y));

        col = mix(col, vec3(0.0, 0.85, 0.55), line * 0.55);
        col = mix(col, vec3(1.0, 0.30, 0.15), border);
    }

    if (u_handles > 0.5) {
        // Draw the four corner handles in projector space so they sit exactly
        // where you click, whatever the warp is doing to the content.
        vec2 pa = vec2(puv.x * u_paspect, puv.y);
        for (int i = 0; i < 4; i++) {
            vec2 ca = vec2(u_corners[i].x * u_paspect, u_corners[i].y);
            float d = distance(pa, ca);
            float dot_  = 1.0 - smoothstep(0.010, 0.014, d);
            float ring = (1.0 - smoothstep(0.024, 0.028, d))
                       * smoothstep(0.018, 0.022, d);
            vec3 tint = (i == u_sel) ? vec3(1.0, 0.85, 0.15)
                                     : vec3(0.25, 0.75, 1.0);
            col = mix(col, tint, clamp(dot_ + ring, 0.0, 1.0));
        }
    }

    f_color = vec4(col, 1.0);
}
"""


class BowRenderer:
    def __init__(self, ctx, content_size=(1280, 800), fade=0.055):
        self.ctx = ctx
        self.content_size = content_size
        self.fade = fade
        self.show_grid = False

        self._quad = ctx.buffer(_QUAD.tobytes())
        self.prog_fade = ctx.program(vertex_shader=_VERT, fragment_shader=_FADE_FRAG)
        self.prog_stroke = ctx.program(vertex_shader=_VERT, fragment_shader=_STROKE_FRAG)
        self.prog_warp = ctx.program(vertex_shader=_VERT, fragment_shader=_WARP_FRAG)

        self.vao_fade = ctx.simple_vertex_array(self.prog_fade, self._quad, "in_pos")
        self.vao_stroke = ctx.simple_vertex_array(self.prog_stroke, self._quad, "in_pos")
        self.vao_warp = ctx.simple_vertex_array(self.prog_warp, self._quad, "in_pos")

        # Float texture so the additive trails can accumulate past 1.0 before
        # being tone-mapped down by the fade.
        self.accum_tex = ctx.texture(content_size, 4, dtype="f2")
        self.accum_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.accum_fbo = ctx.framebuffer(color_attachments=[self.accum_tex])
        self.accum_fbo.use()
        ctx.clear(0.0, 0.0, 0.0, 1.0)

    def release(self):
        for obj in (self.accum_fbo, self.accum_tex, self._quad,
                    self.prog_fade, self.prog_stroke, self.prog_warp):
            try:
                obj.release()
            except Exception:
                pass

    def render(self, frame, screen_fbo, screen_size, warp,
               handles=False, selected=0):
        """frame: a RenderFrame of normalized bow data. Draws one output frame."""
        ctx = self.ctx
        cw, ch = self.content_size

        # --- passes 1 & 2: update the accumulation buffer ---
        self.accum_fbo.use()
        ctx.viewport = (0, 0, cw, ch)
        ctx.enable(moderngl.BLEND)

        ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.prog_fade["u_fade"].value = self.fade
        self.vao_fade.render(moderngl.TRIANGLE_STRIP)

        ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        p = self.prog_stroke
        p["u_a"].value = frame.a
        p["u_b"].value = frame.b
        p["u_speed"].value = frame.speed
        p["u_angle"].value = frame.angle
        p["u_time"].value = frame.time
        p["u_aspect"].value = cw / ch
        p["u_ok"].value = 1.0 if frame.ok else 0.0
        self.vao_stroke.render(moderngl.TRIANGLE_STRIP)

        # --- pass 3: warp onto the calibrated quad ---
        screen_fbo.use()
        ctx.viewport = (0, 0, *screen_size)
        ctx.disable(moderngl.BLEND)
        ctx.clear(0.0, 0.0, 0.0, 1.0)

        self.accum_tex.use(0)
        self.prog_warp["u_tex"].value = 0
        self.prog_warp["u_grid"].value = 1.0 if self.show_grid else 0.0
        self.prog_warp["u_handles"].value = 1.0 if handles else 0.0
        self.prog_warp["u_sel"].value = int(selected)
        self.prog_warp["u_paspect"].value = screen_size[0] / max(screen_size[1], 1)
        self.prog_warp["u_corners"].write(
            np.array(warp.corners, dtype="f4").tobytes())
        # GLSL mat3 is column-major, so upload the transpose.
        Hinv = np.ascontiguousarray(warp.inverse().T, dtype="f4")
        self.prog_warp["u_Hinv"].write(Hinv.tobytes())
        self.vao_warp.render(moderngl.TRIANGLE_STRIP)
