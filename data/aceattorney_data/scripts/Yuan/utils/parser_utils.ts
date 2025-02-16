function parseContent(contentWrapper: Element): string {
    return contentWrapper.textContent?.trim() || "";
}

export { parseContent };