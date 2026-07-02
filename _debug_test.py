import traceback, pathlib

ROOT = pathlib.Path(r"G:\claude-code-workspace\ReqCollect")
LOG = []

try:
    # Test: Read ProposalListView
    prop_path = ROOT / "reqcollect-web" / "src" / "views" / "proposal" / "ProposalListView.vue"
    prop = prop_path.read_text("utf-8")
    LOG.append(f"OK read ProposalListView ({len(prop)} chars)")
    
    # Check key markers
    checks = [
        ("old_dialog_start", 'prd-gen-body' in prop),
        ("old_state", 'const previewMarkdown = ref<string[]>([])' in prop),
        ("old_marked_import", 'import { marked }' in prop),
        ("old_generate_end", "prdGenerating.value = false" in prop),
        ("old_gen_start", "prdGenerating.value = true" in prop),
        ("old_on_error", "onError: (msg) =>" in prop),
        ("old_on_done", "onDone: () =>" in prop),
        ("old_close_gen", "const closeGen = () =>" in prop),
    ]
    for name, exists in checks:
        LOG.append(f"  {'OK' if exists else 'MISSING'} {name}")
    
    # Test: Read PrdView
    prdview_path = ROOT / "reqcollect-web" / "src" / "views" / "PrdView.vue"
    prdview = prdview_path.read_text("utf-8")
    LOG.append(f"OK read PrdView ({len(prdview)} chars)")
    
    checks2 = [
        ("old_content_section", 'class="prd-content" ref="prdContentRef"' in prdview),
        ("old_actions", 'showWikiDialog' in prdview),
        ("old_toc", '<PrdToc' in prdview),
        ("old_view_wiki", 'const showWikiDialog = ref(false)' in prdview),
        ("ElMessage", 'ElMessage' in prdview),
        ("updatePrd", 'updatePrd' in prdview),
        ("marked", 'import { marked }' in prdview),
    ]
    for name, exists in checks2:
        LOG.append(f"  {'OK' if exists else 'MISSING'} {name}")
    
except Exception as e:
    LOG.append(f"ERROR: {e}")
    LOG.append(traceback.format_exc())

with open(ROOT / "__debug_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
