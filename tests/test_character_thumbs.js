const test = require("node:test");
const assert = require("node:assert/strict");

class MockImage {
  constructor(classNames = [], wrap = null) {
    this.classList = {
      contains(name) {
        return classNames.includes(name);
      },
    };
    this._wrap = wrap;
  }

  closest(selector) {
    if (selector === ".character-thumb-wrap") {
      return this._wrap;
    }
    return null;
  }
}

global.HTMLImageElement = MockImage;

const {
  characterThumbPlaceholderHtml,
  replaceFailedCharacterThumb,
} = require("../static/character_thumbs.js");

test("characterThumbPlaceholderHtml returns the no-image placeholder markup", () => {
  assert.equal(
    characterThumbPlaceholderHtml(),
    '<div class="character-thumb-placeholder">No image</div>',
  );
});

test("replaceFailedCharacterThumb swaps a failed thumbnail for the placeholder", () => {
  const wrap = { innerHTML: "<button>old</button>" };
  const image = new MockImage(["character-thumb"], wrap);

  const replaced = replaceFailedCharacterThumb(image);

  assert.equal(replaced, true);
  assert.equal(wrap.innerHTML, characterThumbPlaceholderHtml());
});

test("replaceFailedCharacterThumb ignores non-thumbnail targets", () => {
  const wrap = { innerHTML: "<button>old</button>" };
  const image = new MockImage(["other-class"], wrap);

  const replaced = replaceFailedCharacterThumb(image);

  assert.equal(replaced, false);
  assert.equal(wrap.innerHTML, "<button>old</button>");
});
