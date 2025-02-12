function parseContent(contentWrapper: Element): string {
    const textParts: string[] = [];

    // get the text content of the current element
    const text = contentWrapper.textContent?.trim();

    // if the text content is not empty, add it to the text parts
    if (text && text.length > 0) {
        textParts.push(text);
    }
    
    // Process each child element
    for (const child of Array.from(contentWrapper.children)) {

        // Get text content and clean it
        const text = child.textContent?.trim();
        if (text && text.length > 0) {
            textParts.push(text);
        }
    }

    // Join all text parts with newlines
    return textParts.join("\n");
}

export { parseContent };