// The service worker has one job (spec section 3): open the side panel when the toolbar button or Alt+R is used.
const openOnClick = () => chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {})
chrome.runtime.onInstalled.addListener(openOnClick)
chrome.runtime.onStartup.addListener(openOnClick)
