/******************************************************************************
 *
 * Copyright (c) 2017, the Perspective Authors.
 *
 * This file is part of the Perspective library, distributed under the terms of
 * the Apache License 2.0.  The full license can be found in the LICENSE file.
 *
 */

const selected_position_map = new WeakMap();

function write(table, model, active_cell) {
    const meta = table.getMeta(active_cell);
    if (meta) {
        let text = active_cell.textContent;
        const id = model._ids[meta.y - meta.y0];

        const msg = {
            __INDEX__: id,
            [model._column_paths[meta.x]]: text
        };
        model._table.update([msg], {port_id: model._edit_port});
    }
}

async function moveSelection(table, active_cell, dx, dy) {
    const meta = table.getMeta(active_cell);
    const num_columns = this._column_paths.length;
    const num_rows = this._num_rows;
    const selected_position = selected_position_map.get(table);
    if (!selected_position) {
        return;
    }
    if (meta.x + dx < num_columns && 0 <= meta.x + dx) {
        selected_position.x = meta.x + dx;
    }

    if (meta.y + dy < num_rows && 0 <= meta.y + dy) {
        selected_position.y = meta.y + dy;
    }

    while (!focusStyleListener(table)) {
        table.scrollToCell(meta.x0 + dx, meta.y0 + dy, num_columns, num_rows);
        await table.draw();
        selected_position_map.set(table, selected_position);
        dx += dx / Math.abs(dx || 1);
        dy += dy / Math.abs(dy || 1);
    }
}

function isEditable(viewer) {
    const has_pivots = this._config.row_pivots.length === 0 && this._config.column_pivots.length === 0;
    const selectable = viewer.hasAttribute("selectable");
    return has_pivots && !selectable;
}

function getPos() {
    if (this.isContentEditable) {
        let _range = document.getSelection().getRangeAt(0);
        let range = _range.cloneRange();
        range.selectNodeContents(this);
        range.setEnd(_range.endContainer, _range.endOffset);
        return range.toString().length;
    } else {
        return this.target.selectionStart;
    }
}

// Styles

function editableStyleListener(table, viewer) {
    const edit = isEditable.call(this, viewer);
    for (const td of table.querySelectorAll("td")) {
        const meta = table.getMeta(td);
        const type = this._schema[this._column_paths[meta.x]];
        td.toggleAttribute("contenteditable", edit && type === "string");
    }
}

const focusStyleListener = table => {
    const tds = table.querySelectorAll("td");
    const selected_position = selected_position_map.get(table);
    if (selected_position) {
        for (const td of tds) {
            const meta = table.getMeta(td);
            if (meta.x === selected_position.x && meta.y === selected_position.y) {
                if (document.activeElement !== td) {
                    td.focus({preventScroll: true});
                }
                return true;
            }
        }
        if (document.activeElement !== document.body && table.contains(document.activeElement)) {
            document.activeElement.blur();
        }
    }
};

// Events

function keydownListener(table, event) {
    if (!isEditable.call(this, table)) return;
    const target = document.activeElement;
    switch (event.keyCode) {
        case 13:
            event.preventDefault();
            if (event.shiftKey) {
                moveSelection.call(this, table, target, 0, -1);
            } else {
                moveSelection.call(this, table, target, 0, 1);
            }
            break;
        case 37:
            if (getPos.call(target) == 0) {
                event.preventDefault();
                moveSelection.call(this, table, target, -1, 0);
            }
            break;
        case 38:
            event.preventDefault();
            moveSelection.call(this, table, target, 0, -1);
            break;
        case 39:
            if (getPos.call(target) == target.textContent.length) {
                event.preventDefault();
                moveSelection.call(this, table, target, 1, 0);
            }
            break;
        case 40:
            event.preventDefault();
            moveSelection.call(this, table, target, 0, 1);
            break;
        default:
    }
}

function focusoutListener(table, viewer, event) {
    if (isEditable.call(this, viewer) && selected_position_map.has(table)) {
        const selectedPosition = selected_position_map.get(table);
        selected_position_map.delete(table);
        if (selectedPosition.content !== event.target.textContent) {
            write(table, this, event.target);
        }
    }
}

function focusinListener(table, viewer, event) {
    const meta = table.getMeta(event.target);
    if (meta) {
        const new_state = {x: meta.x, y: meta.y, content: event.target.textContent};
        selected_position_map.set(table, new_state);
    }
}

// Plugin

export async function configureEditable(table, viewer) {
    this._edit_port = await viewer.getEditPort();
    table.addStyleListener(editableStyleListener.bind(this, table, viewer));
    table.addStyleListener(focusStyleListener.bind(this, table, viewer));
    table.addEventListener("focusin", focusinListener.bind(this, table, viewer));
    table.addEventListener("focusout", focusoutListener.bind(this, table, viewer));
    table.addEventListener("keydown", keydownListener.bind(this, table));
}
