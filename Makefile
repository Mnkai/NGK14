ROCKBOX_TOOLS ?= $(HOME)/src/rockbox/tools
CONVBDF       ?= $(ROCKBOX_TOOLS)/convbdf

CFG           := build/fonts.yml

# --- default NGK14 ---
OUT_BDF       := dist/bdf/NGK14-14.bdf
OUT_FNT       := dist/rockbox/14-NGK14.fnt

ROCKBOX14     := src/upstream/rockbox-14-Nimbus.bdf
GALMURI11     := src/upstream/galmuri11.bdf
K12           := src/upstream/k12-2000-1.bdf

# --- padded variant (built from patch) ---
TMP_DIR          := build/.tmp
ROCKBOX14_PAD_IN := $(TMP_DIR)/rockbox-14-Nimbus_padded.bdf
OUT_BDF_PAD      := dist/bdf/NGK14-padded-14.bdf
OUT_FNT_PAD      := dist/rockbox/14-NGK14-padded.fnt
PATCH_PAD        := patches/rockbox-14-Nimbus_padded.patch

all: $(OUT_FNT) $(OUT_FNT_PAD)

# --- NGK14 ---
$(OUT_BDF): build/bdf_merge.py $(CFG) $(ROCKBOX14) $(GALMURI11) $(K12)
	mkdir -p dist/bdf
	python3 build/bdf_merge.py --align center --keep-metrics -o $(OUT_BDF) $(ROCKBOX14) $(GALMURI11) $(K12)

$(OUT_FNT): $(OUT_BDF)
	mkdir -p dist/rockbox
	$(CONVBDF) -f -o $(OUT_FNT) $(OUT_BDF) 

# --- NGK14-padded ---
$(ROCKBOX14_PAD_IN): $(ROCKBOX14) $(PATCH_PAD)
	mkdir -p $(TMP_DIR)
	cp $(ROCKBOX14) $@
	patch --silent $@ $(PATCH_PAD)

$(OUT_BDF_PAD): build/bdf_merge.py $(CFG) $(ROCKBOX14_PAD_IN) $(GALMURI11) $(K12)
	mkdir -p dist/bdf
	python3 build/bdf_merge.py --align center --keep-metrics -o $(OUT_BDF_PAD) $(ROCKBOX14_PAD_IN) $(GALMURI11) $(K12)

$(OUT_FNT_PAD): $(OUT_BDF_PAD)
	mkdir -p dist/rockbox
	$(CONVBDF) -f -o $(OUT_FNT_PAD) $(OUT_BDF_PAD) 

clean:
	rm -rf dist $(TMP_DIR)

.PHONY: all clean
