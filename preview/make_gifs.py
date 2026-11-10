import glob, sys
from PIL import Image
out = sys.argv[1]
for name, dur in [("idle",100),("walk",50),("run",50),("attack",50),("stare",100)]:
    fr = [Image.open(f).convert("RGB").resize((400,400), Image.LANCZOS) for f in sorted(glob.glob(f"{name}_*.png"))]
    if name == "attack":
        fr += [fr[-1]] * 8
    fr = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in fr]
    fr[0].save(f"{out}/{name}.gif", save_all=True, append_images=fr[1:], duration=dur, loop=0, optimize=True)
sheet = Image.new("RGB", (5*280, 280))
for i, (n, k) in enumerate([("idle",30),("walk",8),("run",6),("attack",7),("stare",10)]):
    sheet.paste(Image.open(f"{n}_{k:03d}.png").convert("RGB").resize((280,280)), (i*280,0))
sheet.save(f"{out}/sheet.png")
