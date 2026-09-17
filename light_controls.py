"""Global light control styling for the DIENGIN Streamlit UI."""

LIGHT_CONTROLS_CSS = r"""
<style>
/* Keep native Streamlit controls visually aligned with the custom light dashboard. */
html, body, .stApp, [data-testid="stAppViewContainer"]{
  color-scheme:light!important;
}

/* Text / labels */
.stApp label,
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p{
  color:#1E2B3F!important;
}

/* Select / multiselect / date / time / text inputs */
.stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="input"],
.stApp [data-testid="stDateInput"] [data-baseweb="input"],
.stApp [data-testid="stTimeInput"] [data-baseweb="input"]{
  background:#FFFFFF!important;
  border-color:rgba(32,54,82,.14)!important;
  color:#1E2B3F!important;
  box-shadow:none!important;
}
.stApp [data-baseweb="select"] input,
.stApp [data-baseweb="input"] input,
.stApp [data-testid="stDateInput"] input,
.stApp [data-testid="stTimeInput"] input{
  color:#1E2B3F!important;
  -webkit-text-fill-color:#1E2B3F!important;
  caret-color:#2878F0!important;
}
.stApp [data-baseweb="select"] svg,
.stApp [data-baseweb="input"] svg{
  fill:#6F7D91!important;
  color:#6F7D91!important;
}

/* Multiselect chips */
.stApp [data-baseweb="tag"]{
  background:#EAF3FF!important;
  color:#2878F0!important;
  border:1px solid #CFE3FF!important;
  border-radius:8px!important;
}
.stApp [data-baseweb="tag"] span,
.stApp [data-baseweb="tag"] svg{
  color:#2878F0!important;
  fill:#2878F0!important;
}

/* Menus / popovers / calendars */
[data-baseweb="popover"],
[data-baseweb="menu"],
[data-baseweb="calendar"],
[role="listbox"]{
  background:#FFFFFF!important;
  color:#1E2B3F!important;
}
[data-baseweb="menu"] li,
[role="option"]{
  background:#FFFFFF!important;
  color:#1E2B3F!important;
}
[data-baseweb="menu"] li:hover,
[role="option"]:hover{
  background:#F1F6FD!important;
}
[data-baseweb="calendar"] button,
[data-baseweb="calendar"] div{
  color:#1E2B3F!important;
}

/* Standard buttons: white surface; primary buttons stay blue. */
.stApp [data-testid="stBaseButton-secondary"],
.stApp [data-testid="stDownloadButton"] button{
  background:#FFFFFF!important;
  color:#1E2B3F!important;
  border:1px solid rgba(32,54,82,.14)!important;
}
.stApp [data-testid="stBaseButton-primary"]{
  background:#2878F0!important;
  color:#FFFFFF!important;
  border-color:#2878F0!important;
}

/* Focus should use the same DIENGIN blue instead of system/dark accents. */
.stApp [data-baseweb="select"] > div:focus-within,
.stApp [data-baseweb="input"]:focus-within{
  border-color:#2878F0!important;
  box-shadow:0 0 0 1px #2878F0!important;
}
</style>
"""
