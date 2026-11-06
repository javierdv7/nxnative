# The Legend of Zelda: Ocarina of Time (0400486024DEC000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's patches.py and applies those of a
# module's NSO build ID; CUTS, OBS and FRAME_STEP as described there ("Registered patches"). Patches of Nintendo SDK module builds are in dm/tools/sdk_patches.py
from nso_asm import ADRP, B

# main e0f3ccfaf50065ae4ea01eb5aeb13b1a (the v0 base and the v131072 update share it): sead::GameFrameworkOunce (vtable main+0x4c63f80, `fw` below) presents through its interval
# setter main+0x346c5c0 (fw, w1 = vsyncs): nvnWindowSetPresentInterval through the window at fw+0x180, then fw+0xfc = 60 / interval, which the vsync wait (main+0x346c920) and the
# frame-rate getters read. Its one caller is the frame-rate controller (main+0x3b4ef60, object at fw+0x270 = `ctrl`, reached from vtable +0x128 main+0x4dbd60 every frame), which
# calls it at main+0x3b4f088 with ctrl+0x48 also when it is disabled (ctrl+0x60 bit 0 → main+0x3b4f074): the setter runs once a frame. When enabled the controller counts the
# vsyncs the last frame needed from the CPU span (fw+0x148) and the GPU span (fw+0x150, from counter timestamps), clamped to [ctrl+0, ctrl+4], steps up after ctrl+0x10 late
# frames and down later: a 30 fps fallback. The game turns it off itself and fixes the interval: main+0x33723d0 sets ctrl+0x60 and calls setInterval(1) (main+0x3b4f370, which
# also writes ctrl+0x48 and ctrl+0x58 = 60 / interval), main+0x3372400 sets ctrl+0x60 and a rate of its own (main+0x3b4f390), main+0x3372420 turns it back on
# (main+0x3b4f2e0). In gameplay on the Mac the present interval stayed 1 (run logs: "present interval set by the game 1" only, with DM_NVN_GPU_TS=segment too) while frames took
# 25-60 ms, and the game ran slow: its updates are once a frame.
# Unverified: which field the game logic reads for its time step. The controller's 30 fps fallback implies the logic steps by the interval (otherwise the console would play slow
# whenever it stepped up), and the setter is the one place every interval goes through, so the stub hands the host's step to it, as Breath of the Wild's does
# (dm/games/01007EF00011E000/patches.py). If the speed is still wrong at a two-vsync step, the logic's delta source is elsewhere (open: the AI queries QueryGetBaseDeltaTime,
# QueryVFRCounter and IsUseVFR name a VFR whose reader was not found).
# The stub (x16 / x17 are free at the entry: the setter's arguments are x0 and w1): with a target fps on the state page (fps_target), the host's step (state +0x20) replaces w1,
# unless the game has disabled the controller and asks for more than one vsync itself (a fixed lower rate of its own): that interval is kept and published at state +0x24, so
# the host holds frames that long. A disabled controller at interval 1 (the game's fixed 60) takes the host's step: that is the case that played slow. 0 at +0x20 (not decided
# yet) or no target keeps the game's interval
def frame_step(ctx):
    here, emit, fs_site, fs_put, FS_STATE_OFF = ctx.here, ctx.emit, ctx.site, ctx.put, ctx.state
    fs_site(0x346c5c0, '7f2303d5')   # pacibsp
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xb9400211,   # ldr w17,[x16]          target fps (0 = off)
              0x340001d1,   # cbz w17,orig (+14)
              0x394b4011,   # ldrb w17,[x0,#0x2d0]   ctrl+0x60: the game disabled the controller
              0x360000b1,   # tbz w17,#0,host (+5)
              0x7100043f,   # cmp w1,#1
              0x5400006d,   # b.le host (+3)         its fixed 60: the host's step
              0xb9002601,   # str w1,[x16,#0x24]     a fixed lower rate of the game's own: published, kept
              0x14000008,   # b orig (+8)
              0xb900261f,   # host: str wzr,[x16,#0x24]
              0xb9402211,   # ldr w17,[x16,#0x20]    step in vsyncs
              0x340000b1,   # cbz w17,orig (+5)      not decided yet
              0x2a1103e1,   # mov w1,w17
              0xf9401a11,   # ldr x17,[x16,#0x30]
              0x8b214231,   # add x17,x17,w1,uxtw
              0xf9001a11,   # str x17,[x16,#0x30]    vsyncs stepped
              0xd503237f):  # orig: pacibsp
        emit(w)
    emit(B(here(), 0x346c5c4))
    fs_put(0x346c5c0, [B(0x346c5c0, start)], 'GameFrameworkOunce interval setter: the host\'s step unless the game fixes a lower rate itself (state page target fps; 0 = the game\'s interval)')

FRAME_STEP = {'e0f3ccfaf50065ae4ea01eb5aeb13b1a': frame_step}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md): what, its binding now, the loosest it could have (goal),
# purpose, why; blocked or kept: why the gap stays open (cannot close yet, or left open on purpose); checked: what was checked on game files (else a judgement)
BINDING = [
    {'what': 'frame step at the framework interval setter (sead::GameFrameworkOunce)', 'now': 'build', 'goal': 'game', 'purpose': 'frame rate',
     'why': "the game's own framework code at fixed addresses",
     'blocked': 'frame-step stubs have no function-matched form yet'},
]
