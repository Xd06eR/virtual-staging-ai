"""
Streamlit Frontend
The user interface for Virtual Staging AI.
"""
import streamlit as st
import requests
import time
import json
from pathlib import Path
from typing import Optional, Tuple

from app.config import DATA_INPUT_DIR, DATA_OUTPUT_DIR, SAMPLES_DIR

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
FASTAPI_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Virtual Staging AI",
    page_icon="🛋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSS_STYLES = """
<style>
    .stApp { background-color: #f8f9fc; }
    h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 700; color: #2c3e50; letter-spacing: -1px; }
    h2, h3 { color: #34495e; }
    .css-card { background-color: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 2rem; border: 1px solid #eef0f5; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3rem; font-weight: 600; transition: all 0.3s ease; }
    .stImage { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .status-indicator { padding: 0.5rem; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 1rem; }
    .status-online { background-color: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .status-offline { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
</style>
"""

# -----------------------------------------------------------------------------
# Utils & API Client
# -----------------------------------------------------------------------------
class APIClient:
    """Handles communication with the FastAPI backend."""
    
    @staticmethod
    def is_online() -> bool:
        try:
            return requests.get(f"{FASTAPI_URL}/health", timeout=3).status_code == 200
        except requests.exceptions.RequestException:
            return False

    @staticmethod
    def enhance_prompt(description: str) -> dict:
        resp = requests.post(f"{FASTAPI_URL}/enhance-prompt", json={"room_description": description}, timeout=180)
        return resp.json()

    @staticmethod
    def generate_image(prompt: str, description: str, image_path: str, resolution: int) -> dict:
        payload = {
            "enhanced_prompt": prompt,
            "room_description": description,
            "image_path": image_path,
            "target_resolution": resolution
        }
        resp = requests.post(f"{FASTAPI_URL}/generate-image", json=payload, timeout=600)
        return resp.json()

def get_next_filename() -> str:
    """Generates sequential filename for inputs."""
    existing = list(DATA_INPUT_DIR.glob("empty_room_*.*"))
    max_num = 0
    for f in existing:
        try:
            max_num = max(max_num, int(f.stem.split("_")[-1]))
        except ValueError:
            continue
    return f"empty_room_{max_num + 1:05d}"

def save_input_file(file_bytes: bytes, original_name: str) -> Path:
    """Saves bytes to the input directory with sequential naming."""
    ext = Path(original_name).suffix or ".png"
    filename = f"{get_next_filename()}{ext}"
    path = DATA_INPUT_DIR / filename
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path

def get_history() -> list[dict]:
    """Retrieves sorted list of past generations."""
    files = []
    for f in sorted(DATA_OUTPUT_DIR.glob("virtual_staging_*.png"), reverse=True):
        files.append({"path": f, "number": f.stem.split("_")[-1]})
    return files

def get_input_for_output(output_path: Path) -> Optional[Path]:
    """Finds the corresponding input file for a generated image."""
    num = output_path.stem.split("_")[-1]
    for ext in [".png", ".jpg", ".jpeg"]:
        candidate = DATA_INPUT_DIR / f"empty_room_{num}{ext}"
        if candidate.exists():
            return candidate
    return None

def load_metadata(output_path: Path) -> dict:
    """Loads metadata JSON if present."""
    meta_path = output_path.with_suffix(".json")
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not read metadata {meta_path}: {exc}")
    return {}

# -----------------------------------------------------------------------------
# UI Components
# -----------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.markdown("### System Status")
        if APIClient.is_online():
            st.markdown('<div class="status-indicator status-online">● FastAPI Online</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-indicator status-offline">● FastAPI Offline</div>', unsafe_allow_html=True)
            st.warning("Ensure backend is running")
        
        st.divider()
        st.markdown("### ⚡ Quick Start Samples")
        if SAMPLES_DIR.exists():
            for idx, sample in enumerate(list(SAMPLES_DIR.glob("*.*"))):
                if sample.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    st.image(str(sample), use_container_width=True)
                    if st.button("Use", key=f"sample_{idx}"):
                        st.session_state.selected_sample = sample
                        st.rerun()

def render_input_section() -> Tuple[Optional[bytes], Optional[str], Optional[str], Optional[int]]:
    """Renders input column; returns (bytes, name, description, resolution) or all-None."""
    st.markdown("### 1. Upload & Describe")
    container = st.container(border=True)
    
    with container:
        uploaded = st.file_uploader("Upload empty room image", type=["png", "jpg", "jpeg"])
        
        file_bytes = None
        file_name = None
        is_ready = False

        # Priority: Upload > Selected Sample
        if uploaded:
            st.session_state.selected_sample = None
            file_bytes = uploaded.getvalue()
            file_name = uploaded.name
            st.image(uploaded, caption="Uploaded Image", use_container_width=True)
            is_ready = True
        elif st.session_state.get("selected_sample"):
            sample = st.session_state.selected_sample
            try:
                file_bytes = sample.read_bytes()
                file_name = sample.name
                st.image(str(sample), caption=f"Selected Sample: {sample.name}", use_container_width=True)
                if st.button("❌ Clear Selection", type="secondary"):
                    st.session_state.selected_sample = None
                    st.rerun()
                is_ready = True
            except Exception as e:
                st.error(f"Error reading sample: {e}")

        st.markdown("#### Room Details")
        desc = st.text_area("Describe the style and furniture", placeholder="E.g., Scandinavian living room with a grey sofa, oak coffee table, warm lighting, and indoor plants...", height=120)
        
        with st.expander("⚙️ Advanced Settings"):
            res = st.slider(
                label="Resolution (Shortest Side)",
                min_value=768,
                max_value=4096,
                value=1024,
                step=64,
                help="Higher resolution creates sharper images but increases processing time and VRAM usage."
            )
            
        generate = st.button("✨ Generate Staging", type="primary", disabled=not (is_ready and desc))
        
        if generate:
            return file_bytes, file_name, desc, res
            
    return None, None, None, None

def render_result_section():
    st.markdown("### 2. Staged Result")
    
    if "result" in st.session_state:
        res = st.session_state.result
        if res.get("success"):
            out_path = Path(res["image_path"])
            in_path = res.get("input_path")
            
            with st.container(border=True):
                t1, t2 = st.tabs(["🖼️ Side-by-Side", "📝 Prompt Details"])
                with t1:
                    if out_path.exists():
                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption("Original")
                            if in_path and Path(in_path).exists():
                                st.image(in_path, use_container_width=True)
                        with c2:
                            st.caption("Staged")
                            st.image(str(out_path), use_container_width=True)
                        st.success(f"Saved: {out_path.name}")
                    else:
                        st.warning("File missing from disk.")
                with t2:
                    st.info("AI Enhanced Prompt:")
                    st.text_area("Prompt", value=res.get("enhanced_prompt", ""), height=200, disabled=True)
        else:
            st.error(f"Failed: {res.get('error')}")
    else:
        with st.container(border=True):
            st.markdown("<div style='text-align: center; padding: 3rem; color: #aaa;'><h3>👋 Ready to Design</h3></div>", unsafe_allow_html=True)

def render_history():
    st.markdown("---")
    st.markdown("### 📂 Recent Designs")
    files = get_history()[:6]
    if not files:
        st.info("No history yet.")
        return

    cols = st.columns(6)
    for i, item in enumerate(files):
        with cols[i]:
            path = item["path"]
            if path.exists():
                st.image(str(path), use_container_width=True)
                if st.button(f"View #{item['number']}", key=f"hist_{i}"):
                    # Restore state
                    meta = load_metadata(path)
                    st.session_state.result = {
                        "success": True,
                        "image_path": str(path),
                        "input_path": str(get_input_for_output(path) or ""),
                        "enhanced_prompt": meta.get("prompt", "Restored from history")
                    }
                    st.rerun()

# -----------------------------------------------------------------------------
# Main Application Logic
# -----------------------------------------------------------------------------
def main():
    if "selected_sample" not in st.session_state:
        st.session_state.selected_sample = None

    st.markdown(CSS_STYLES, unsafe_allow_html=True)
    render_sidebar()
    
    st.markdown("<h1>🛋️ Virtual Staging AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.2rem; color: #666; margin-bottom: 2rem;'>Transform empty spaces with Local AI.</p>", unsafe_allow_html=True)

    c_input, c_result = st.columns([1, 1.2], gap="large")
    
    with c_input:
        # returns data if button clicked
        f_bytes, f_name, desc, res = render_input_section()
        
    with c_result:
        render_result_section()

    # Handle Generation Trigger
    if f_bytes and desc:
        with st.status("🏗️ AI is working...", expanded=True) as status:
            try:
                st.write("📤 Saving input...")
                input_path = save_input_file(f_bytes, f_name)
                
                st.write("🤖 Enhancing prompt...")
                enh_resp = APIClient.enhance_prompt(desc)
                if not enh_resp.get("success"):
                    raise Exception(enh_resp.get("error"))
                
                st.write(f"🎨 Rendering (Res: {res}px)...")
                start = time.time()
                gen_resp = APIClient.generate_image(
                    enh_resp["enhanced_prompt"], 
                    desc, 
                    str(input_path), 
                    res
                )
                
                if gen_resp.get("success"):
                    st.session_state.result = {
                        "success": True,
                        "image_path": gen_resp["image_path"],
                        "input_path": str(input_path),
                        "enhanced_prompt": gen_resp["enhanced_prompt"]
                    }
                    status.update(label=f"✅ Done ({time.time()-start:.1f}s)", state="complete", expanded=False)
                    st.rerun()
                else:
                    raise Exception(gen_resp.get("error"))
                    
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(str(e))

    render_history()

if __name__ == "__main__":
    main()