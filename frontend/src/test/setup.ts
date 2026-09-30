// jsdom doesn't implement scrolling; the router and catalog pagination call it.
window.scrollTo = () => {}
