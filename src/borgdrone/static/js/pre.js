function select_tab(tabId) {
    let tab_selector = document.getElementById('sidebar_links')

    for (let i = 0; i < tab_selector.children.length; i++) {
        if (tab_selector.children[i].id === tabId) {
            tab_selector.children[i].classList.add('selected')
        } else {
            tab_selector.children[i].classList.remove('selected')
        }
    }
}
