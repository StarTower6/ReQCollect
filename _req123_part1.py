"""
Three requirements:
  1. PRD Tab inline (WorkspaceDetail + PrdListView)
  2. Dialog three-phase (ProposalListView)
  3. PRD Markdown edit (backend update_prd + pm endpoint + PrdView)
"""
import pathlib

ROOT = pathlib.Path(r"G:\claude-code-workspace\ReqCollect")
LOG = []

def log(msg):
    LOG.append(msg)
    print(msg)

# ════════════════════════════════════════════════════════════════
# BACKEND: update_prd abstract method + implementations
# ════════════════════════════════════════════════════════════════

# 1a. __init__.py — add abstract update_prd after list_prds_by_workspace
init_path = ROOT / "app" / "db" / "__init__.py"
init = init_path.read_text("utf-8")

abstract_update = '''
    @abstractmethod
    async def update_prd(self, prd_id: str, **kwargs) -> dict | None:
        """Update PRD fields (markdown, title, etc). Returns updated PRD or None."""

'''

# Insert before "# ── Dashboard / Stats ──"
marker_init = "    # ── Dashboard / Stats ──"
if marker_init in init and "async def update_prd" not in init:
    init = init.replace(marker_init, abstract_update + marker_init)
    init_path.write_text(init, "utf-8")
    log("OK __init__.py: added abstract update_prd")
else:
    log("SKIP __init__.py: update_prd already exists or marker not found")

# 1b. repository.py — add MySQL update_prd
repo_path = ROOT / "app" / "db" / "repository.py"
repo = repo_path.read_text("utf-8")

repo_update = '''
    async def update_prd(self, prd_id: str, **kwargs) -> dict | None:
        """Update PRD fields. Returns updated PRD or None."""
        async with await self._get_session() as s:
            result = await s.execute(
                select(GeneratedPRD).where(GeneratedPRD.id == prd_id)
            )
            prd = result.scalar_one_or_none()
            if not prd:
                return None
            for key, val in kwargs.items():
                if val is not None and hasattr(prd, key):
                    setattr(prd, key, val)
            await s.commit()
            await s.refresh(prd)
            return prd.to_dict()
'''

marker_repo = "            return [p.to_dict() for p in prds]\n"
if marker_repo in repo and "async def update_prd" not in repo:
    repo = repo.replace(marker_repo, marker_repo + repo_update)
    repo_path.write_text(repo, "utf-8")
    log("OK repository.py: added update_prd")
else:
    log("SKIP repository.py: update_prd already exists or marker not found")

# 1c. compat.py — add File update_prd
compat_path = ROOT / "app" / "db" / "compat.py"
compat = compat_path.read_text("utf-8")

compat_update = '''
    async def update_prd(self, prd_id: str, **kwargs) -> dict | None:
        """Update PRD fields. Returns updated PRD or None."""
        # Find and update in-memory, then persist
        all_prds = self._load_all_prds()
        updated = None
        for p in all_prds:
            if p.get("id") == prd_id:
                for key, val in kwargs.items():
                    if val is not None:
                        p[key] = val
                updated = p
                break
        if updated is None:
            return None
        # Persist back to the session's PRD file
        sid = updated.get("session_id", "")
        if sid:
            path = self._prds_path(sid)
            existing = self._load_json(path) or []
            for i, ep in enumerate(existing):
                if ep.get("id") == prd_id:
                    existing[i] = updated
                    break
            _FileLock.write_json(path, existing)
        return updated
'''

marker_compat = "            reverse=True,\n        )\n"
if marker_compat in compat and "async def update_prd" not in compat:
    compat = compat.replace(marker_compat, marker_compat + compat_update)
    compat_path.write_text(compat, "utf-8")
    log("OK compat.py: added update_prd")
else:
    log("SKIP compat.py: update_prd already exists or marker not found")

# 1d. pm.py — add PATCH /pm/prd/by-id/{prd_id}
pm_path = ROOT / "app" / "api" / "pm.py"
pm = pm_path.read_text("utf-8")

# Add PrdUpdateBody model before the class or before pm_generate_from_proposals
prd_update_model = '''
class PrdUpdateBody(BaseModel):
    markdown: str
    title: str | None = None


'''

# Find a good insertion point — after the last BaseModel class before pm_generate_from_proposals
marker_pm = "class GenerateFromProposalsRequest(BaseModel):"
if marker_pm in pm and "class PrdUpdateBody" not in pm:
    pm = pm.replace(marker_pm, prd_update_model + marker_pm)
    log("OK pm.py: added PrdUpdateBody model")
else:
    log("SKIP pm.py: PrdUpdateBody already exists or marker not found")

# Add the endpoint before the last route
pm_endpoint = '''
@router.patch("/pm/prd/by-id/{prd_id}")
async def pm_update_prd(
    prd_id: str,
    body: PrdUpdateBody,
    current_user: dict = Depends(require_prd_generator),
):
    """Update PRD markdown (edit mode save)."""
    ds = get_datastore()
    updated = await ds.update_prd(prd_id, markdown=body.markdown, title=body.title)
    if not updated:
        raise HTTPException(404, "PRD not found")
    return {"success": True, "prd": updated}
'''

# Find a good place — after pm_get_prd_by_id or before the last endpoint
marker_pm2 = '@router.get("/pm/prd/by-id/{prd_id}")'
if marker_pm2 in pm and "async def pm_update_prd" not in pm:
    pm = pm.replace(marker_pm2, pm_endpoint + "\n" + marker_pm2)
    log("OK pm.py: added pm_update_prd endpoint")
else:
    log("SKIP pm.py: pm_update_prd already exists or marker not found")

pm_path.write_text(pm, "utf-8")

log("\n=== Backend done ===")

# ════════════════════════════════════════════════════════════════
# FRONTEND
# ════════════════════════════════════════════════════════════════

# 2. api/prd.ts — add updatePrd
prd_api_path = ROOT / "reqcollect-web" / "src" / "api" / "prd.ts"
prd_api = prd_api_path.read_text("utf-8")

update_prd_fn = '''
/** Update PRD markdown (edit mode save) */
export async function updatePrd(prdId: string, body: { markdown: string; title?: string }): Promise<PrdRecord> {
  const data = await apiPatch<{ success: boolean; prd: PrdRecord }>(`/pm/prd/by-id/${encodeURIComponent(prdId)}`, body)
  return data.prd
}
'''

if "export async function updatePrd" not in prd_api:
    # Add at end of file
    prd_api += "\n" + update_prd_fn
    prd_api_path.write_text(prd_api, "utf-8")
    log("OK prd.ts: added updatePrd")
else:
    log("SKIP prd.ts: updatePrd already exists")

# 3. WorkspaceDetail.vue — inline PrdListView for prds tab
wsd_path = ROOT / "reqcollect-web" / "src" / "views" / "WorkspaceDetail.vue"
wsd = wsd_path.read_text("utf-8")

# 3a. Replace prds tab template
old_tab = '''      <el-tab-pane label="📄 PRD文档" name="prds">
        <div v-if="!workspace" v-loading="true" style="height:200px" />
        <div v-else class="prds-placeholder">
          <p>PRD 文档列表</p>
          <el-button type="primary" size="small" @click="router.push(`/workspaces/${route.params.id}/prds`)">
            查看全部 PRD →
          </el-button>
        </div>
      </el-tab-pane>'''

new_tab = '''      <el-tab-pane label="📄 PRD文档" name="prds">
        <div v-if="!workspace" v-loading="true" style="height:200px" />
        <PrdListView v-else-if="activeTab === 'prds'" :workspace-id="route.params.id as string" :embedded="true" />
      </el-tab-pane>'''

if old_tab in wsd:
    wsd = wsd.replace(old_tab, new_tab)
    log("OK WorkspaceDetail: replaced prds tab template")
else:
    log("WARN WorkspaceDetail: old prds tab template not found")

# 3b. Remove watch redirect for prds tab
old_watch = """// Prds tab redirects to dedicated list page
if (tab === 'prds') {
  router.push(`/workspaces/${route.params.id}/prds`)
  return
}"""

new_watch = ""

if old_watch in wsd:
    wsd = wsd.replace(old_watch, new_watch)
    log("OK WorkspaceDetail: removed prds tab redirect")
else:
    log("WARN WorkspaceDetail: prds tab redirect not found (may already be removed)")

# 3c. Add PrdListView import
old_import = "import ProposalKanbanView from './proposal/ProposalKanbanView.vue'"
new_import = "import ProposalKanbanView from './proposal/ProposalKanbanView.vue'\nimport PrdListView from './PrdListView.vue'"

if old_import in wsd and "import PrdListView" not in wsd:
    wsd = wsd.replace(old_import, new_import)
    log("OK WorkspaceDetail: added PrdListView import")
else:
    log("SKIP WorkspaceDetail: PrdListView import already exists or base not found")

wsd_path.write_text(wsd, "utf-8")

# 4. PrdListView.vue — add props + embedded mode
plv_path = ROOT / "reqcollect-web" / "src" / "views" / "PrdListView.vue"
plv = plv_path.read_text("utf-8")

# 4a. Update defineProps
old_props = "const route = useRoute()"
new_props = '''const props = defineProps<{
  workspaceId?: string
  embedded?: boolean
}>()

const route = useRoute()'''

if old_props in plv and "defineProps" not in plv:
    plv = plv.replace(old_props, new_props)
    log("OK PrdListView: added props")
else:
    log("SKIP PrdListView: props already exist or marker not found")

# 4b. Update wid computation
old_wid = "const wid = computed(() => route.params.id as string)"
new_wid = "const wid = computed(() => props.workspaceId || (route.params.id as string))"

if old_wid in plv:
    plv = plv.replace(old_wid, new_wid)
    log("OK PrdListView: updated wid computed")
else:
    log("WARN PrdListView: old wid not found")

# 4c. Hide return button and outer padding when embedded
old_return_btn = '''    <div class="prd-list-header">
      <el-button text @click="router.back()" class="back-btn">← 返回</el-button>
      <h2>PRD 文档</h2>
    </div>'''

new_return_btn = '''    <div class="prd-list-header" v-if="!props.embedded">
      <el-button text @click="router.back()" class="back-btn">← 返回</el-button>
      <h2>PRD 文档</h2>
    </div>'''

if old_return_btn in plv:
    plv = plv.replace(old_return_btn, new_return_btn)
    log("OK PrdListView: conditional return button")
else:
    log("WARN PrdListView: old header not found")

# 4d. Add embedded class to outer div
old_outer = '<div class="prd-list-page">'
new_outer = '<div class="prd-list-page" :class="{ embedded: props.embedded }">'

if old_outer in plv:
    plv = plv.replace(old_outer, new_outer)
    log("OK PrdListView: embedded class binding")
else:
    log("WARN PrdListView: outer div not found")

# 4e. Add embedded style
old_style_end = "</style>"
new_style_end = '''
.prd-list-page.embedded {
  padding: 0;
}
</style>'''

if old_style_end in plv and ".embedded" not in plv:
    plv = plv.replace(old_style_end, new_style_end)
    log("OK PrdListView: added embedded style")
else:
    log("SKIP PrdListView: embedded style already exists")

plv_path.write_text(plv, "utf-8")

log("\n=== Requirement 1 done ===")
log(f"\nChanges applied. Check {len(LOG)} log entries above.")
