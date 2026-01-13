---
title: "A tool for Domo management"
url: /c/builders-club/a-tool-for-domo-management
author: Andrew Chaffin
published_date: May 24, 2021
updated_date: Jun 20, 2022 at 05:29 AM
tags: ['Master Hacker']
categories: ['Get Help']
likes: 4
---
# A tool for Domo management
**Author:** Andrew Chaffin
**Published:** May 24, 2021
**Tags:** Master Hacker
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeWVvRFE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--8f1ce274209cfa30af1e467021d29ac2dcdead37/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Stay%20up%20to%20speed%20with%20Data%20Strategy%20(8).png)

---

This has long been a dream of ours - build a tool that makes life as a Domo administrator just a bit easier. Here's our v1.1. We'd love your feedback! Also, if you wanna buy it, just email me at [andrew@crystalballers.ai](mailto:andrew@crystalballers.ai)﻿

media-controller {
font-size: 13px;
font-family: Roboto, Arial, sans-serif;
--media-font-family: Roboto, helvetica neue, segoe ui, arial, sans-serif;
-webkit-font-smoothing: antialiased;
--media-secondary-color: transparent;
--media-menu-background: rgba(28, 28, 28, 0.9);
--media-control-hover-background: var(--media-secondary-color);
--media-range-track-height: 3px;
--media-range-thumb-height: 13px;
--media-range-thumb-width: 13px;
--media-range-thumb-border-radius: 13px;
--media-preview-thumbnail-border: 2px solid #fff;
--media-preview-thumbnail-border-radius: 2px;
--media-tooltip-display: none;
}

media-controller[mediaisfullscreen] {
font-size: 17px;
--media-range-thumb-height: 20px;
--media-range-thumb-width: 20px;
--media-range-thumb-border-radius: 10px;
--media-range-track-height: 4px;
}

.control-button {
position: relative;
display: inline-block;
width: 36px;
padding: 0 2px;
height: 100%;
opacity: 0.9;
transition: opacity 0.1s cubic-bezier(0.4, 0, 1, 1);
}

[breakpointmd] .control-button {
width: 48px;
}

[mediaisfullscreen] .control-button {
width: 54px;
}

.control-button svg {
height: 100%;
width: 100%;
fill: var(--media-primary-color, #fff);
fill-rule: evenodd;
}

.svg-shadow {
stroke: #000;
stroke-opacity: 0.15;
stroke-width: 2px;
fill: none;
}

.gradient-bottom {
padding-top: 37px;
position: absolute;
width: 100%;
height: 170px;
bottom: 0;
pointer-events: none;
background-position: bottom;
background-repeat: repeat-x;
background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAACqCAYAAABsziWkAAAAAXNSR0IArs4c6QAAAQVJREFUOE9lyNdHBQAAhfHb3nvvuu2997jNe29TJJEkkkgSSSSJJJJEEkkiifRH5jsP56Xz8PM5gcC/xfDEmjhKxEOCSaREEiSbFEqkQppJpzJMJiWyINvkUCIX8kw+JQqg0BRRxaaEEqVQZsopUQGVpooS1VBjglStqaNEPTSYRko0QbNpoUQrtJl2qsN0UqILuk0PJXqhz/RTYgAGzRA1bEYoMQpjZpwSExAyk5SYgmkzQ82aOUqEIWKilJiHBbNIiSVYhhVYhTVYhw3YhC3Yhh3YhT3YhwM4hCM4hhM4hTM4hwu4hCu4hhu4hTu4hwd4hCd4hhd4hTd4hw/4hC/4hh/4/QM2/id28uIEJAAAAABJRU5ErkJggg==');
}

media-settings-menu {
position: absolute;
border-radius: 12px;
right: 12px;
bottom: 61px;
z-index: 70;
will-change: width, height;
text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
transition: opacity 0.1s cubic-bezier(0, 0, 0.2, 1);
user-select: none;
--media-settings-menu-min-width: 220px;
}

[mediaisfullscreen] media-settings-menu {
--media-settings-menu-min-width: 320px;
right: 24px;
bottom: 70px;
}

media-settings-menu-item {
height: 40px;
font-size: 13px;
font-weight: 500;
padding-top: 0;
padding-bottom: 0;
}

[mediaisfullscreen] media-settings-menu-item {
font-size: 20px;
height: 50px;
}

media-settings-menu-item[submenusize='0'] {
display: none;
}

.quality-settings[submenusize='1'] {
display: none;
}

{{playbackspeedlabel ?? 'Playback speed'}}

{{playbackspeedlabel ?? 'Playback speed'}}

{{qualitylabel ?? 'Quality'}}

{{qualitylabel ?? 'Quality'}}

{{subtitleslabel ?? 'Subtitles/CC'}}

{{subtitleslabel ?? 'Subtitles/CC'}}

media-time-range {
position: absolute;
overflow-x: clip;
bottom: 36px;
width: 100%;
height: 5px;
--media-range-track-background: rgba(255, 255, 255, 0.2);
--media-range-track-pointer-background: rgba(255, 255, 255, 0.5);
--media-time-range-buffered-color: rgba(255, 255, 255, 0.4);
--media-range-bar-color: var(--media-accent-color, rgb(229, 9, 20));
--media-range-thumb-border-radius: 13px;
--media-range-thumb-background: var(--media-accent-color, #f00);
--media-range-thumb-transition: transform 0.1s linear;
--media-range-thumb-transform: scale(0) translate(0%, 0%);
}

media-time-range:hover {
--media-range-track-height: 5px;
--media-range-thumb-transform: scale(1) translate(0%, 0%);
}

[breakpointmd] media-time-range {
bottom: 47px;
}

[mediaisfullscreen] media-time-range {
bottom: 52.5px;
height: 8px;
}

[mediaisfullscreen] media-time-range:hover {
--media-range-track-height: 8px;
}

media-preview-thumbnail {
margin-bottom: 5px;
}

media-preview-chapter-display {
padding-block: 0;
}

media-preview-time-display {
padding-top: 0;
}

media-control-bar {
position: absolute;
height: 36px;
line-height: 36px;
bottom: 0;
left: 12px;
right: 12px;
}

[breakpointmd] media-control-bar {
height: 48px;
line-height: 48px;
}

[mediaisfullscreen] media-control-bar {
height: 54px;
line-height: 54px;
}

media-play-button {
--media-button-icon-width: 30px;
padding: 6px 10px;
}

media-play-button #icon-play,
media-play-button #icon-pause {
filter: drop-shadow(0 0 2px #00000080);
}

media-play-button :is(#play-p1, #play-p2, #pause-p1, #pause-p2) {
transition: clip-path 0.25s ease-in;
}

media-play-button:not([mediapaused]) #play-p2,
media-play-button:not([mediapaused]) #play-p2 {
transition: clip-path 0.35s ease-in;
}

media-play-button :is(#pause-p1, #pause-p2),
media-play-button[mediapaused] :is(#play-p1, #play-p2) {
clip-path: inset(0);
}

media-play-button #play-p1 {
clip-path: inset(0 100% 0 0);
}

media-play-button #play-p2 {
clip-path: inset(0 20% 0 100%);
}

media-play-button[mediapaused] #pause-p1 {
clip-path: inset(50% 0 50% 0);
}

media-play-button[mediapaused] #pause-p2 {
clip-path: inset(50% 0 50% 0);
}

media-mute-button :is(#icon-muted, #icon-volume) {
transition: clip-path 0.3s ease-out;
}

media-mute-button #icon-muted {
clip-path: inset(0 0 100% 0);
}

media-mute-button[mediavolumelevel='off'] #icon-muted {
clip-path: inset(0);
}

media-mute-button #icon-volume {
clip-path: inset(0);
}

media-mute-button[mediavolumelevel='off'] #icon-volume {
clip-path: inset(100% 0 0 0);
}

media-mute-button #volume-high,
media-mute-button[mediavolumelevel='off'] #volume-high {
opacity: 1;
transition: opacity 0.3s;
}

media-mute-button[mediavolumelevel='low'] #volume-high,
media-mute-button[mediavolumelevel='medium'] #volume-high {
opacity: 0.2;
}

media-volume-range {
height: 36px;
--media-range-track-background: rgba(255, 255, 255, 0.2);
}

media-mute-button + media-volume-range {
width: 0;
overflow: hidden;
transition: width 0.2s ease-in;
}

media-mute-button:hover + media-volume-range,
media-mute-button:focus + media-volume-range,
media-mute-button:focus-within + media-volume-range,
media-volume-range:hover,
media-volume-range:focus,
media-volume-range:focus-within {
width: 70px;
}

media-time-display {
padding-top: 6px;
padding-bottom: 6px;
font-size: 13px;
white-space: nowrap;
}

[mediaisfullscreen] media-time-display {
font-size: 20px;
}

.control-spacer {
flex-grow: 1;
}

media-captions-button {
position: relative;
}

media-captions-button:not([mediasubtitleslist]) svg {
opacity: 0.3;
}

media-captions-button[mediasubtitleslist]:after {
content: '';
display: block;
position: absolute;
width: 0;
height: 3px;
border-radius: 3px;
background-color: var(--media-accent-color, #f00);
bottom: 19%;
left: 50%;
transition:
all 0.1s cubic-bezier(0, 0, 0.2, 1),
width 0.1s cubic-bezier(0, 0, 0.2, 1);
}

media-captions-button[mediasubtitleslist][aria-checked='true']:after {
left: 25%;
width: 50%;
transition:
left 0.25s cubic-bezier(0, 0, 0.2, 1),
width 0.25s cubic-bezier(0, 0, 0.2, 1);
}

media-captions-button[mediasubtitleslist][aria-checked='true']:after {
left: 25%;
width: 50%;

transition:
left 0.25s cubic-bezier(0, 0, 0.2, 1),
width 0.25s cubic-bezier(0, 0, 0.2, 1);
}

media-settings-menu-button svg {
transition: transform 0.1s cubic-bezier(0.4, 0, 1, 1);
transform: rotateZ(0deg);
}

media-settings-menu-button[aria-expanded='true'] svg {
transform: rotateZ(30deg);
}

[mediaisfullscreen] .download-button {
display: none;
}

.download-button:focus-visible {
box-shadow: inset 0 0 0 2px rgb(27 127 204 / .9);
outline: 0;
}
}

[

]({{downloadurl}})

media-fullscreen-button path {
translate: 0% 0%;
}

media-fullscreen-button:hover path {
animation: 0.35s up-left-bounce cubic-bezier(0.34, 1.56, 0.64, 1);
}

media-fullscreen-button:hover .up-right-bounce {
animation-name: up-right-bounce;
}

media-fullscreen-button:hover .down-left-bounce {
animation-name: down-left-bounce;
}

media-fullscreen-button:hover .down-right-bounce {
animation-name: down-right-bounce;
}

@keyframes up-left-bounce {
0% {
translate: 0 0;
}
50% {
translate: -4% -4%;
}
}

@keyframes up-right-bounce {
0% {
translate: 0 0;
}
50% {
translate: 4% -4%;
}
}

@keyframes down-left-bounce {
0% {
translate: 0 0;
}
50% {
translate: -4% 4%;
}
}

@keyframes down-right-bounce {
0% {
translate: 0 0;
}
50% {
translate: 4% 4%;
}
}

media-controller[mediacurrenttime^='0'] .desktop-centered-animation svg {
display: none !important;
animation-name: none !important;
opacity: 0 !important;
}

@media (width  svg {
width: 3rem;
height: 3rem;
opacity: 0;
transform: scale(1);
pointer-events: none;
display: none;
animation: none !important;
}

media-controller:not([mediacurrenttime^='0']) .desktop-centered-animation media-play-button > svg[slot='play'],
media-controller:not([mediacurrenttime^='0']) .desktop-centered-animation media-play-button > svg[slot='pause'] {
display: block;
animation: fadeScale 1s ease-out forwards;
}

@keyframes fadeScale {
0% {
opacity: 1;
transform: scale(1);
}
100% {
opacity: 0;
transform: scale(2);
}
}

.mobile-centered-controls {
display: flex;
align-self: stretch;
align-items: center;
flex-flow: row nowrap;
justify-content: center;
margin: -5% auto 0;
width: 100%;
gap: 1rem;
}

.mobile-centered-controls [role='button'] {
--media-icon-color: var(--media-primary-color, #fff);
background: rgba(0, 0, 0, 0.5);
--media-button-icon-width: 36px;
--media-button-icon-height: 36px;
border-radius: 50%;
user-select: none;
aspect-ratio: 1;
}

.mobile-centered-controls media-play-button {
width: 5rem;
}

.mobile-centered-controls :is(media-seek-backward-button, media-seek-forward-button) {
width: 3rem;
padding: 0.5rem;
}

@media (width >= 768px) {
.mobile-centered-controls {
display: none;
}
}

﻿
