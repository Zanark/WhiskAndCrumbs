import test from 'node:test';
import assert from 'node:assert/strict';
import { bakeryView, bakeryLight, projectPoint } from '../web/bakery-view.mjs';

test('the default camera looks horizontally from eye level and is pulled back', () => {
  for (const [width,height] of [[844,300],[310,248],[609,117],[1000,600]]) {
    const view=bakeryView(width,height);
    assert.deepEqual(view.eye,[0,1.65,8.4]);
    assert.deepEqual(view.target,[0,1.65,-2.5]);
    for (const z of [-.5,-3,-6]) {
      const point=projectPoint(view.matrix,[1,view.eye[1],z],width,height);
      assert.ok(Math.abs(point.y-height/2)<.0001, 'An eye-level horizontal line must not slope down with depth.');
    }
    const left=projectPoint(view.matrix,[-2.5,1.25,-.5],width,height);
    const right=projectPoint(view.matrix,[2.5,1.25,-.5],width,height);
    assert.ok(left.x>0 && right.x<width, 'The pulled-back view must contain the display width.');
  }
});

test('the bakery uses one finite perspective camera across aspect ratios', () => {
  for (const [w,h] of [[1000,600],[320,480],[1024,300]]) {
    for (const x of [-1,0,1]) for (const y of [-1,0,1]) {
      const view=bakeryView(w,h,x,y);
      assert.ok([...view.matrix].every(Number.isFinite));
      const target=projectPoint(view.matrix,view.target,w,h);
      assert.ok(Math.abs(target.x-w/2)<.01 && Math.abs(target.y-h/2)<.01);
      assert.ok(target.visible && target.depth>-1 && target.depth<1);
    }
  }
});
test('look-around is strong, depth dependent and leaves shared floor contacts coincident', () => {
  const left=bakeryView(1000,600,-1,0),right=bakeryView(1000,600,1,0);
  const shift=point=>projectPoint(left.matrix,point,1000,600).x-projectPoint(right.matrix,point,1000,600).x;
  assert.ok(Math.abs(shift([0,1,-.5]))>150);
  assert.ok(Math.abs(shift([0,1,-.5]))>Math.abs(shift([0,1,-6])));
  for (const view of [left,right]) {
    const cabinetFoot=[1,0,-.5],floorContact=[1,0,-.5];
    assert.deepEqual(projectPoint(view.matrix,cabinetFoot,1000,600),projectPoint(view.matrix,floorContact,1000,600));
  }
});
test('sunlight is a fixed left-window direction, not a camera-attached lamp', () => {
  const light=bakeryLight();
  assert.ok(light.direction[0]<0 && light.direction[1]>0);
  assert.ok(Math.abs(Math.hypot(...light.direction)-1)<1e-8);
  assert.ok([...light.matrix].every(Number.isFinite));
  assert.deepEqual(bakeryLight(),light);
});
test('counter contact remains framed on short views and looking down reveals more floor', () => {
  const center=bakeryView(850,240),down=bakeryView(850,240,0,1);
  const contact=[0,0,-.45];
  const a=projectPoint(center.matrix,contact,850,240),b=projectPoint(down.matrix,contact,850,240);
  assert.ok(a.y>0 && a.y<230);
  assert.ok(b.y<a.y-25);
});
test('invalid view sizes fail explicitly and extreme pointer coordinates are bounded', () => {
  for (const value of [0,-1,NaN,Infinity]) assert.throws(()=>bakeryView(value,600),RangeError);
  assert.deepEqual(bakeryView(1000,600,999,-999),bakeryView(1000,600,1,-1));
});
