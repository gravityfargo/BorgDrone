function select_tab(tabId) {
    let tab_selector = document.getElementById('sidebar_links')

    for (let i = 0; i < tab_selector.children.length; i++) {
        if (tab_selector.children[i].id === tabId) {
            let nav_link = tab_selector.children[i].children[0]
            nav_link.classList.add('active')
        } else {
            let nav_link = tab_selector.children[i].children[0]
            nav_link.classList.remove('active')
        }
    }
}

function select_sub_tab(tabId) {
    let tabs = document.getElementById('sub-header')
    for (let i = 0; i < tabs.children.length; i++) {
        let tab = tabs.children[i]
        console.log(tab)

        if (tab.id === tabId) {
            tab.classList.add('active')
        } else {
            tab.classList.remove('active')
        }
    }
}
