(function initCharacterThumbs(globalScope) {
  function characterThumbPlaceholderHtml() {
    return '<div class="character-thumb-placeholder">No image</div>';
  }

  function replaceFailedCharacterThumb(image) {
    if (!(image instanceof globalScope.HTMLImageElement) || !image.classList.contains("character-thumb")) {
      return false;
    }
    const thumbWrap = image.closest(".character-thumb-wrap");
    if (!thumbWrap) {
      return false;
    }
    thumbWrap.innerHTML = characterThumbPlaceholderHtml();
    return true;
  }

  const api = {
    characterThumbPlaceholderHtml,
    replaceFailedCharacterThumb,
  };

  globalScope.CharacterThumbs = api;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
}(typeof globalThis !== "undefined" ? globalThis : this));
