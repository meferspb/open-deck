/**
 * Реестр типов приборов. Чтобы добавить новый прибор, достаточно создать
 * модуль с классом-наследником Widget и зарегистрировать его здесь.
 */

import { AnnunciatorWidget } from './annunciator.js';
import { AttitudeWidget } from './attitude.js';
import { AltimeterWidget } from './altimeter.js';
import { HeadingWidget } from './heading.js';
import { KnobWidget } from './knob.js';
import { RadialGaugeWidget } from './radial-gauge.js';
import { ReadoutWidget } from './readout.js';
import { ToggleSwitchWidget } from './toggle-switch.js';
import { UnknownWidget } from './unknown.js';
import { VsiWidget } from './vsi.js';

/** @type {Map<string, new (element: HTMLElement, ctx: any, def: any) => any>} */
const REGISTRY = new Map([
  ['attitude', AttitudeWidget],
  ['gauge.radial', RadialGaugeWidget],
  ['readout', ReadoutWidget],
  ['switch.toggle', ToggleSwitchWidget],
  ['knob.rotary', KnobWidget],
  ['annunciator', AnnunciatorWidget],
  ['vsi', VsiWidget],
  ['altimeter', AltimeterWidget],
  ['heading', HeadingWidget],
]);

export function supportedTypes() {
  return [...REGISTRY.keys()];
}

/**
 * @param {any} def
 * @param {HTMLElement} element
 * @param {any} ctx
 */
export function createWidgetInstance(def, element, ctx) {
  const WidgetClass = REGISTRY.get(def?.type) ?? UnknownWidget;
  return new WidgetClass(element, ctx, def);
}
